"""Installed Codex entrypoints preserve the original extraction contracts."""
from contextlib import closing
import json
from pathlib import Path
import sqlite3
import subprocess
import sys

from support import CodexFixture


class ExtractionContracts(CodexFixture):
    def assert_cli_error(self, script, *arguments, message=None):
        result = self.run_script(script, *arguments)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(result.stdout, "")
        self.assertTrue(result.stderr.startswith("ERROR:"), result.stderr)
        self.assertNotIn("Traceback", result.stderr)
        if message:
            self.assertIn(message.lower(), result.stderr.lower())

    def database_history(self, item):
        self.history.unlink()
        with closing(sqlite3.connect(self.home / "state_1.sqlite")) as db, db:
            db.execute("CREATE TABLE threads (id TEXT, cwd TEXT, rollout_path TEXT)")
            db.execute("INSERT INTO threads VALUES (?, ?, ?)", (self.sid, str(self.project), None))
        with closing(sqlite3.connect(self.home / "thread_history_1.sqlite")) as db, db:
            db.execute("CREATE TABLE thread_items (thread_id TEXT, item_json TEXT, rollout_ordinal INTEGER, created_at_ms INTEGER)")
            from datetime import datetime
            db.execute("INSERT INTO thread_items VALUES (?, ?, ?, ?)",
                       (self.sid, item, 1, int(datetime.now().timestamp() * 1000)))

    def test_latest_prints_actual_rollout_path(self):
        latest = self.run_script("latest_session.py")
        self.assertEqual(latest.returncode, 0, latest.stderr)
        self.assertEqual(Path(latest.stdout.strip()), self.history)

    def test_cleaner_prints_complete_original_schema_with_optional_source(self):
        for arguments in [(str(self.history),), ()]:
            with self.subTest(arguments=arguments):
                cleaned = self.run_script("chat_context_extractor.py", *arguments)
                self.assertEqual(cleaned.returncode, 0, cleaned.stderr)
                data = json.loads(cleaned.stdout)
                self.assertEqual(set(data), {"session_id", "custom_title", "model", "date",
                    "first_ts", "last_ts", "turns", "files_modified", "session_count",
                    "project_root", "total_user", "total_assistant"})
                self.assertEqual(len(data["turns"]), 28)
                self.assertIsInstance(data["files_modified"], list)
                self.assertTrue(all(isinstance(turn["tools"], list) for turn in data["turns"]))
                self.assertEqual(data["turns"][-1]["text"], "Conversation 28")
                self.assertEqual(data["session_id"], self.sid)
                self.assertEqual(data["total_user"], 14)
                self.assertEqual(data["total_assistant"], 14)

    def test_today_prints_original_presentation_records_and_deduplicates_markdown_uuid(self):
        result = self.run_script("extract_today.py")
        self.assertEqual(result.returncode, 0, result.stderr)
        rows = json.loads(result.stdout)
        self.assertIsInstance(rows, list)
        self.assertEqual(len(rows), 1)
        self.assertEqual(set(rows[0]), {"path", "uuid", "mtime", "size_kb"})
        self.assertEqual(rows[0]["path"], str(self.history))
        self.assertEqual(rows[0]["uuid"], self.sid)
        self.assertEqual(rows[0]["size_kb"], round(self.history.stat().st_size / 1024))
        folder = self.project / "chat-contexts"
        folder.mkdir()
        (folder / "saved.md").write_text(f"---\nsession_id: {self.sid}\n---\nSaved note\n", encoding="utf-8")
        result = self.run_script("extract_today.py")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout), [])

    def test_extraction_creates_no_intermediate_json_files_or_directories(self):
        before = set(self.project.rglob("*"))
        for script in ("latest_session.py", "chat_context_extractor.py", "extract_today.py"):
            result = self.run_script(script)
            self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(set(self.project.rglob("*")), before)

    def test_cross_project_cleaning_reports_error(self):
        other = self.base / "other-project"
        other.mkdir()
        self.rows[0]["payload"]["cwd"] = str(other)
        self.write_history()
        self.assert_cli_error("chat_context_extractor.py", str(self.history), message="does not belong")

    def test_sqlite_errors_use_error_exit_path(self):
        (self.home / "state_1.sqlite").write_bytes(b"not a sqlite database")
        for script in ("latest_session.py", "chat_context_extractor.py", "extract_today.py"):
            with self.subTest(script=script):
                self.assert_cli_error(script, message="database")

    def test_database_json_errors_use_error_exit_path(self):
        self.database_history("{invalid-json")
        for script in ("latest_session.py", "chat_context_extractor.py", "extract_today.py"):
            with self.subTest(script=script):
                self.assert_cli_error(script, message="Expecting")

    def test_malformed_metadata_uses_actionable_error_exit_path(self):
        self.rows[0]["payload"] = None
        self.write_history()
        cases = (("latest_session.py", ()),
                 ("chat_context_extractor.py", ()),
                 ("chat_context_extractor.py", (str(self.history),)),
                 ("extract_today.py", ()))
        for script, arguments in cases:
            with self.subTest(script=script, arguments=arguments):
                self.assert_cli_error(script, *arguments,
                                      message="malformed or unsupported Codex history")

    def test_database_only_selection_truthfully_rejects_missing_rollout(self):
        self.database_history(json.dumps(self.rows[1]["payload"]))
        self.assert_cli_error("latest_session.py", message="rollout file")
        result = self.run_script("extract_today.py")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout), [])
        self.assertIn("rollout file", result.stderr)

    def test_bootstrap_creates_usable_helper_and_reruns(self):
        helper = self.project / ".intern101" / "find_project_dir.py"
        result = self.run_script("project_index_manager.py")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "bootstrapped")
        self.assertTrue(helper.is_file())
        before = helper.read_bytes()
        result = self.run_script("project_index_manager.py")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "bootstrapped")
        self.assertEqual(helper.read_bytes(), before)
        code = ("import sys; sys.path.insert(0,sys.argv[1]); "
                "from find_project_dir import find_project_dir; "
                "print(find_project_dir(sys.argv[2]))")
        result = subprocess.run([sys.executable, "-c", code, str(helper.parent), str(self.project)],
                                cwd=self.project, env=self.env, capture_output=True,
                                text=True, encoding="utf-8")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(Path(result.stdout.strip()), self.history.parent)

    def test_bootstrap_preserves_existing_project_helper_bytes(self):
        helper = self.project / ".intern101" / "find_project_dir.py"
        helper.parent.mkdir()
        before = b"# Existing project helper\r\ndef find_project_dir(cwd=None):\r\n    return 'keep'\r\n"
        helper.write_bytes(before)
        result = self.run_script("project_index_manager.py")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "bootstrapped")
        self.assertEqual(helper.read_bytes(), before)
