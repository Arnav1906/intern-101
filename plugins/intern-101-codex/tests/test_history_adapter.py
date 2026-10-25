"""Original cleaned-session and real rollout filesystem contracts."""
import ast
from contextlib import closing
import json
import os
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from support import CodexFixture

class HistoryAdapterTests(CodexFixture):
    def assert_adapter_error(self, function, *arguments, message):
        result = self.adapter_process(function, *arguments)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(message.lower(), result.stderr.lower())

    def test_complete_cleaned_session_matches_original_contract(self):
        before = self.history.read_bytes()
        result = self.adapter("clean_session", str(self.history), str(self.project))
        self.assertEqual(len(result["turns"]), 28)
        self.assertEqual(result["session_id"], self.sid)
        self.assertEqual(result["total_user"], 14)
        self.assertEqual(result["total_assistant"], 14)
        self.assertEqual(set(result), {"session_id", "custom_title", "model", "date",
            "first_ts", "last_ts", "turns", "files_modified", "session_count",
            "project_root", "total_user", "total_assistant"})
        self.assertEqual(result["custom_title"], "")
        self.assertEqual(result["project_root"], str(self.project.resolve()))
        self.assertEqual(result["session_count"], 1)
        self.assertEqual(result["date"], datetime.now().strftime("%Y-%m-%d"))
        self.assertEqual(result["turns"][-1]["text"], "Conversation 28")
        self.assertEqual(self.history.read_bytes(), before)
        self.assertFalse((self.project / ".intern101" / "prepared").exists())

    def test_project_runtime_ignores_unrelated_claude_history(self):
        fake = Path(self.env["CLAUDE_PLUGIN_ROOT"]) / "sessions"
        fake.mkdir(parents=True)
        (fake / "fake.jsonl").write_text(self.history.read_text(encoding="utf-8"), encoding="utf-8")
        self.assertEqual(self.adapter("runtime"), [str(self.project.resolve()), str(self.home.resolve())])
        self.assertEqual(self.adapter("latest_session_path"), str(self.history.resolve()))
        self.history.unlink()
        self.assert_adapter_error("latest_session_path", message="No matching Codex session")

    def test_explicit_cross_project_is_rejected_and_discovery_excludes_it(self):
        other = self.base / "other-project"
        other.mkdir()
        foreign = self.history.parent / "foreign.jsonl"
        rows = json.loads(json.dumps(self.rows))
        rows[0]["payload"].update(cwd=str(other), id="22222222-2222-4222-8222-222222222222")
        foreign.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")
        self.assert_adapter_error("clean_session", str(foreign), str(self.project), message="does not belong")
        self.assertEqual([row["uuid"] for row in self.adapter("todays_new_sessions")], [self.sid])
        self.assertEqual(self.adapter("list_todays_jsonl", str(self.home), str(self.project)), [str(self.history)])

    def test_empty_malformed_and_tool_only_conversations_raise(self):
        for tail in ["", "{not-json\n", json.dumps({"type": "response_item", "payload": {
                "type": "function_call", "name": "exec_command", "arguments": "echo tools"}}) + "\n"]:
            with self.subTest(tail=tail):
                self.history.write_text(json.dumps(self.rows[0]) + "\n" + tail, encoding="utf-8")
                self.assert_adapter_error("clean_session", str(self.history), message="No readable conversation")
                result = self.adapter_process("todays_new_sessions")
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(json.loads(result.stdout), [])
                self.assertIn(self.sid, result.stderr)
                self.assertEqual(self.adapter("list_todays_jsonl", str(self.home), str(self.project)), [])

    def test_metadata_only_paginated_session_does_not_block_readable_today_session(self):
        skipped_id = "22222222-2222-4222-8222-222222222222"
        yesterday = datetime.now().astimezone() - timedelta(days=1)
        unreadable = self.history.parent / "metadata-only.jsonl"
        rows = [
            {"type": "session_meta", "timestamp": yesterday.isoformat(),
             "payload": {"id": skipped_id, "cwd": str(self.project),
                         "timestamp": yesterday.isoformat(), "history_mode": "paginated"}},
            {"type": "event_msg", "timestamp": yesterday.isoformat(),
             "payload": {"type": "thread_settings_applied"}},
        ]
        unreadable.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")
        with closing(sqlite3.connect(self.home / "thread_history_1.sqlite")) as db, db:
            db.execute("CREATE TABLE thread_items (thread_id TEXT, item_json TEXT, rollout_ordinal INTEGER, created_at_ms INTEGER)")
        result = self.run_script("extract_today.py")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual([row["uuid"] for row in json.loads(result.stdout)], [self.sid])
        self.assertIn(skipped_id, result.stderr)
        self.assertIn("No readable conversation", result.stderr)
        self.assert_adapter_error("clean_session", str(unreadable), str(self.project), message="No readable conversation")

    def test_missing_session_id_is_rejected(self):
        del self.rows[0]["payload"]["id"]
        self.write_history()
        self.assert_adapter_error("clean_session", str(self.history), message="no session ID")

    def test_known_markdown_uuid_styles_and_configured_context_folder(self):
        folder = self.project / "saved notes"
        folder.mkdir()
        for index, quote in enumerate(["", "'", '"']):
            (folder / f"note-{index}.md").write_text(
                f"---\nsession_id: {quote}{self.sid}{quote}\n---\nSaved context\n", encoding="utf-8")
        nested = folder / "nested"
        nested.mkdir()
        second = "22222222-2222-4222-8222-222222222222"
        (nested / "other.md").write_text(f"---\nsession_id: '{second}'\n---\n", encoding="utf-8")
        self.assertEqual(ast.literal_eval(self.adapter("known_session_ids", str(folder))), {self.sid, second})
        config = self.project / ".intern101"
        config.mkdir()
        (config / "config.json").write_text(json.dumps({"contexts_dir": "saved notes"}), encoding="utf-8")
        self.assertEqual(self.adapter("todays_new_sessions"), [])
        self.assertEqual(self.adapter("list_todays_jsonl", str(self.home), str(self.project)), [str(self.history)])

    def test_missing_context_folder_has_no_known_ids(self):
        self.assertEqual(self.adapter("known_session_ids", str(self.project / "missing")), "set()")
        result = self.adapter("todays_new_sessions")
        self.assertEqual(len(result), 1)
        self.assertEqual(set(result[0]), {"path", "uuid", "mtime", "size_kb"})
        self.assertEqual(result[0]["path"], str(self.history))
        self.assertEqual(result[0]["uuid"], self.sid)
        self.assertEqual(result[0]["size_kb"], round(self.history.stat().st_size / 1024))
        self.assertEqual(result[0]["mtime"], datetime.fromtimestamp(self.history.stat().st_mtime).strftime("%H:%M"))

    def test_continued_session_uses_activity_and_original_first_date(self):
        yesterday = datetime.now().astimezone() - timedelta(days=1)
        for row in self.rows:
            row["timestamp"] = yesterday.isoformat()
        self.rows[0]["payload"]["timestamp"] = yesterday.isoformat()
        self.write_history()
        self.assertEqual(self.adapter("todays_new_sessions"), [])
        self.assertEqual(self.adapter("list_todays_jsonl", str(self.home), str(self.project)), [])
        self.rows[-1]["timestamp"] = datetime.now().astimezone().isoformat()
        self.write_history()
        self.assertEqual([row["uuid"] for row in self.adapter("todays_new_sessions")], [self.sid])
        self.assertEqual(self.adapter("list_todays_jsonl", str(self.home), str(self.project)), [str(self.history)])
        self.assertEqual(self.adapter("clean_session")["date"], yesterday.strftime("%Y-%m-%d"))

    def test_latest_uses_conversation_activity_and_today_sorts_mtime(self):
        other = self.history.parent / "other.jsonl"
        second = "22222222-2222-4222-8222-222222222222"
        rows = json.loads(json.dumps(self.rows))
        rows[0]["payload"]["id"] = second
        later = datetime.now().astimezone().replace(hour=15, minute=30)
        for row in rows[1:]:
            row["timestamp"] = later.isoformat()
        other.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")
        morning = later.replace(hour=8).timestamp()
        evening = later.replace(hour=18).timestamp()
        os.utime(other, (morning, morning))
        os.utime(self.history, (evening, evening))
        self.assertEqual(self.adapter("latest_session_path"), str(other))
        self.assertEqual([row["uuid"] for row in self.adapter("todays_new_sessions")], [second, self.sid])

    def test_partial_last_record_is_ignored_without_modifying_history(self):
        with self.history.open("a", encoding="utf-8") as stream:
            stream.write('{"type":"response_item","payload":')
        before = self.history.read_bytes()
        self.assertEqual(len(self.adapter("clean_session")["turns"]), 28)
        self.assertEqual(len(self.adapter("todays_new_sessions")), 1)
        self.assertEqual(self.history.read_bytes(), before)

    def test_database_only_session_fails_filesystem_contract_explicitly(self):
        self.history.unlink()
        state = self.home / "state_1.sqlite"
        with closing(sqlite3.connect(state)) as db, db:
            db.execute("CREATE TABLE threads (id TEXT, cwd TEXT, rollout_path TEXT)")
            db.execute("INSERT INTO threads VALUES (?, ?, ?)", (self.sid, str(self.project), None))
        history = self.home / "thread_history_1.sqlite"
        with closing(sqlite3.connect(history)) as db, db:
            db.execute("CREATE TABLE thread_items (thread_id TEXT, item_json TEXT, rollout_ordinal INTEGER, created_at_ms INTEGER)")
            db.execute("INSERT INTO thread_items VALUES (?, ?, ?, ?)", (
                self.sid, json.dumps(self.rows[1]["payload"]), 1, int(datetime.now().timestamp() * 1000)))
        before = {path: path.read_bytes() for path in (state, history)}
        self.assert_adapter_error("latest_session_path", message="rollout file")
        result = self.adapter_process("todays_new_sessions")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout), [])
        self.assertIn("rollout file", result.stderr)
        self.assertEqual(self.adapter("list_todays_jsonl", str(self.home), str(self.project)), [])
        self.assertEqual({path: path.read_bytes() for path in before}, before)
