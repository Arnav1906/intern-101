import importlib.util
import json
import os
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from contextlib import closing
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

REPOSITORY = Path(__file__).resolve().parents[2]
PLUGIN = REPOSITORY / "plugins" / "intern-101-codex"
SCRIPT = PLUGIN / "scripts" / "intern101.py"
sys.path.insert(0, str(PLUGIN / "scripts"))
from lib.codex_sessions import discover, prepare
from lib.contexts import save, read_contexts
from lib.workspace import codex_home, contexts_dir, project_root


class RuntimeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.root = self.base / "work project"
        self.root.mkdir()
        (self.root / ".git").mkdir()
        self.home = self.base / "codex"
        (self.home / "sessions").mkdir(parents=True)
        self.sid = "test-session-1"

    def rollout(self, sid=None, cwd=None, records=None, mode="legacy", meta_extra=None):
        sid = sid or self.sid
        path = self.home / "sessions" / (sid + ".jsonl")
        meta = {"id": sid, "cwd": str(cwd or self.root), "history_mode": mode,
                "timestamp": "2026-10-01T10:00:00Z"}
        meta.update(meta_extra or {})
        rows = [{"timestamp": meta["timestamp"], "type": "session_meta", "payload": meta}]
        rows.extend(records if records is not None else [
            self.message("user", "Fix authentication"), self.message("assistant", "Fixed the login check.")])
        path.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")
        return path

    @staticmethod
    def message(role, text, timestamp="2026-10-01T10:00:00Z"):
        return {"timestamp": timestamp, "type": "response_item", "payload": {
            "type": "message", "role": role, "content": [{"type": "input_text" if role == "user" else "output_text", "text": text}]}}

    def data(self):
        return prepare(discover(self.home, self.root)[0], self.home, self.root)

    @staticmethod
    def summary(title="Authentication fix"):
        return {"title": title, "summary": "Fixed the login check.", "accomplishments": ["Fixed authentication"],
                "decisions": ["Keep the validation at the boundary"], "next_steps": ["Verify the redirect"]}

    def run_cli(self, *args, cwd=None):
        return subprocess.run([sys.executable, str(SCRIPT), "--project", str(cwd or self.root),
                               "--codex-home", str(self.home), *args], capture_output=True, text=True)

    def test_project_matching_includes_descendants_and_excludes_siblings(self):
        sub = self.root / "src"
        sub.mkdir()
        sibling = self.base / "work project-v2"
        sibling.mkdir()
        self.rollout()
        self.rollout("sub", sub)
        self.rollout("sibling", sibling)
        self.rollout("agent", meta_extra={"parent_thread_id": self.sid})
        self.assertEqual({s["id"] for s in discover(self.home, self.root)}, {self.sid, "sub"})

    def test_archive_requires_opt_in(self):
        path = self.rollout()
        archived = self.home / "archived_sessions"
        archived.mkdir()
        path.rename(archived / path.name)
        self.assertEqual(discover(self.home, self.root), [])
        self.assertEqual(len(discover(self.home, self.root, True)), 1)

    def test_legacy_messages_filter_instruction_injections_and_reasoning(self):
        self.rollout(records=[self.message("user", "# AGENTS.md instructions\nsecret instructions"),
                              self.message("user", "<environment_context>metadata</environment_context>Fix login"),
                              {"type": "response_item", "payload": {"type": "reasoning", "text": "private chain"}},
                              self.message("assistant", "Done.")])
        data = self.data()
        self.assertEqual(data["total_user"], 1)
        self.assertEqual(data["turns"][0]["text"], "Fix login")
        self.assertNotIn("private chain", json.dumps(data))

    def test_paginated_completions_dont_duplicate_response_messages(self):
        item = {"type": "UserMessage", "id": "u1", "content": [{"type": "text", "text": "Fix login"}]}
        self.rollout(mode="paginated", records=[self.message("user", "Fix login"),
                     {"timestamp": "2026-10-01T10:00:00Z", "type": "event_msg", "payload": {"type": "item_completed", "item": item}},
                     self.message("assistant", "Fixed.")])
        self.assertEqual(self.data()["total_user"], 1)

    def test_paginated_completion_only_history_is_readable(self):
        rows = [{"timestamp": "2026-10-01T10:00:00Z", "type": "event_msg", "payload": {
            "type": "item_completed", "item": {"type": kind, "content": text}}}
            for kind, text in [("UserMessage", "Fix login"), ("AgentMessage", "Fixed.")]]
        self.rollout(mode="paginated", records=rows)
        data = self.data()
        self.assertEqual([t["text"] for t in data["turns"]], ["Fix login", "Fixed."])

    def test_mixed_message_formats_preserve_assistant_outcome(self):
        self.rollout(mode="paginated", records=[self.message("user", "Fix login"),
                     {"timestamp": "2026-10-01T10:00:00Z", "type": "event_msg", "payload": {
                         "type": "item_completed", "item": {"type": "AgentMessage", "content": "Fixed login."}}}])
        self.assertEqual(self.data()["total_assistant"], 1)

    def test_sqlite_history_is_read_without_mutating_database(self):
        db_path = self.home / "state_123.sqlite"
        with closing(sqlite3.connect(db_path)) as db:
            db.execute("CREATE TABLE threads (id TEXT,cwd TEXT,rollout_path TEXT,history_mode TEXT)")
            db.execute("INSERT INTO threads VALUES (?,?,?,?)", (self.sid, str(self.root), "", "paginated"))
            db.commit()
        item_path = self.home / "thread_history_123.sqlite"
        with closing(sqlite3.connect(item_path)) as db:
            db.execute("CREATE TABLE thread_items (thread_id TEXT,item_json TEXT,rollout_ordinal INTEGER,created_at_ms INTEGER)")
            db.execute("INSERT INTO thread_items VALUES (?,?,?,?)", (self.sid, json.dumps({"type": "userMessage", "content": [{"type": "text", "text": "Fix login"}]}), 1, 1790848800000))
            db.commit()
        before = (db_path.read_bytes(), item_path.read_bytes())
        self.assertEqual(self.data()["total_user"], 1)
        self.assertEqual(before, (db_path.read_bytes(), item_path.read_bytes()))

    def test_tools_preserve_changed_paths_without_outputs(self):
        self.rollout(records=[self.message("user", "Fix login"), {"type": "response_item", "payload": {
            "type": "custom_tool_call", "name": "apply_patch", "input": "*** Begin Patch\n*** Update File: login.py\n*** End Patch"}},
            {"type": "response_item", "payload": {"type": "function_call_output", "output": "secret tool output"}}])
        data = self.data()
        self.assertEqual(data["files_modified"], ["login.py"])
        self.assertNotIn("secret tool output", json.dumps(data))

    def test_metadata_only_session_is_an_error(self):
        self.rollout(records=[], mode="paginated")
        result = self.run_cli("sessions")
        self.assertEqual(result.returncode, 0)
        output = json.loads(result.stdout)
        self.assertEqual(output["sessions"], [])
        self.assertIn("unsupported", output["errors"][0]["error"])
        result = self.run_cli("prepare", "--session", self.sid)
        self.assertNotEqual(result.returncode, 0)

    def test_incomplete_final_line_does_not_lose_readable_history(self):
        path = self.rollout()
        with path.open("a") as stream:
            stream.write('{"type":')
        self.assertEqual(self.data()["total_user"], 1)

    def test_snapshot_save_catchup_recall_daily_update_and_dedup(self):
        self.rollout()
        snapshot = self.root / ".intern101" / "prepared.json"
        result = self.run_cli("prepare", "--session", self.sid, "--output", str(snapshot))
        self.assertEqual(result.returncode, 0, result.stderr)
        input_path = self.root / ".intern101" / "summary.json"
        input_path.write_text(json.dumps(self.summary()), encoding="utf-8")
        result = self.run_cli("save", "--prepared", str(snapshot), "--input", str(input_path))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(Path(json.loads(result.stdout)["path"]).exists())
        self.assertEqual(len(json.loads(self.run_cli("catchup").stdout)["sessions"]), 1)
        self.assertEqual(len(json.loads(self.run_cli("recall", "redirect").stdout)["sessions"]), 1)
        date = self.data()["date"]
        daily = json.loads(self.run_cli("daily-update", "--date", date).stdout)
        self.assertIn("Accomplishments", daily["sessions"][0]["sections"])
        self.assertEqual(json.loads(self.run_cli("sessions", "--new").stdout)["sessions"], [])

    def test_continued_session_saves_new_note_and_daily_uses_latest(self):
        path = self.rollout()
        save(self.root, self.data(), self.summary())
        with path.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(self.message("assistant", "Verified redirect.", "2026-10-01T11:00:00Z")) + "\n")
        self.assertEqual(len(json.loads(self.run_cli("sessions", "--new").stdout)["sessions"]), 1)
        save(self.root, self.data(), self.summary("Authentication verified"))
        self.assertEqual(len(read_contexts(self.root)), 2)
        daily = json.loads(self.run_cli("daily-update", "--date", self.data()["date"]).stdout)
        self.assertEqual(len(daily["sessions"]), 1)
        self.assertEqual(daily["sessions"][0]["title"], "Authentication verified")

    def test_save_preserves_existing_notes_and_valid_table(self):
        self.rollout()
        data = self.data()
        first = save(self.root, data, self.summary("Login | fix"))
        content = Path(first["path"]).read_bytes()
        data["fingerprint"] = "changed"
        second = save(self.root, data, self.summary("Login | fix"))
        self.assertNotEqual(first["path"], second["path"])
        self.assertEqual(Path(first["path"]).read_bytes(), content)
        index = (self.root / "chat-contexts" / "INDEX.md").read_text()
        for row in [r for r in index.splitlines() if "login-fix" in r]:
            self.assertEqual(len(row.strip("|").split("|")), 4)

    def test_output_escape_and_foreign_snapshot_are_rejected(self):
        (self.root / ".intern101").mkdir()
        (self.root / ".intern101" / "config.json").write_text(json.dumps({"contexts_dir": "../outside"}))
        with self.assertRaises(ValueError):
            contexts_dir(self.root)
        self.rollout()
        data = self.data()
        data["project_root"] = str(self.base)
        with self.assertRaises(ValueError):
            save(self.root, data, self.summary())
        self.assertNotEqual(self.run_cli("prepare", "--session", self.sid, "--output", "../escape.json").returncode, 0)

    def test_lock_prevents_conflicting_index_writes(self):
        self.rollout()
        folder = self.root / "chat-contexts"
        folder.mkdir()
        (folder / ".intern101-write.lock").touch()
        with self.assertRaises(ValueError):
            save(self.root, self.data(), self.summary())
        self.assertFalse((folder / "INDEX.md").exists())

    def test_retry_repairs_index_after_interrupted_save(self):
        self.rollout()
        data = self.data()
        with patch("lib.contexts.atomic_write", side_effect=OSError("interrupted")):
            with self.assertRaises(OSError):
                save(self.root, data, self.summary())
        result = save(self.root, data, self.summary())
        self.assertEqual(result["status"], "already_saved")
        self.assertIn(Path(result["path"]).name, Path(result["index"]).read_text())
        self.assertEqual(len(read_contexts(self.root)), 1)

    def test_config_and_environment_precedence_and_nested_root(self):
        folder = self.root / ".intern101"
        folder.mkdir()
        (folder / "config.json").write_text(json.dumps({"codex_home": "custom-home"}))
        nested = self.root / "src"
        nested.mkdir()
        self.assertEqual(project_root(nested), self.root)
        with patch.dict(os.environ, {"CODEX_HOME": str(self.home)}):
            self.assertEqual(codex_home(self.root), self.root / "custom-home")
            self.assertEqual(codex_home(self.root, str(self.home)), self.home)

    def test_activity_dates_use_message_timestamps(self):
        self.rollout(records=[self.message("user", "Fix login", "2026-09-30T10:00:00Z"),
                              self.message("assistant", "Fixed.", "2026-10-01T10:00:00Z")])
        data = self.data()
        expected = datetime.fromisoformat("2026-10-01T10:00:00+00:00").astimezone().strftime("%Y-%m-%d")
        self.assertEqual(data["date"], expected)
        self.assertEqual(len(json.loads(self.run_cli("sessions", "--date", expected).stdout)["sessions"]), 1)


if __name__ == "__main__":
    unittest.main()
