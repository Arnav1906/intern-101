"""Exercise the Codex extraction CLI without project-local JSON handoffs."""

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


CLI = Path(__file__).resolve().parents[1] / "scripts" / "intern101.py"
SESSION_ID = "11111111-1111-4111-8111-111111111111"


class InMemoryExtractionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.project = self.base / "project"
        self.project.mkdir()
        (self.project / ".git").mkdir()
        self.home = self.base / "codex-home"
        sessions = self.home / "sessions" / "2026" / "10" / "10"
        sessions.mkdir(parents=True)
        self.history = sessions / f"rollout-{SESSION_ID}.jsonl"
        self.events = [
            {"timestamp": "2026-10-10T08:00:00Z", "type": "session_meta", "payload": {
                "id": SESSION_ID, "cwd": str(self.project), "timestamp": "2026-10-10T08:00:00Z"}},
            self.message("2026-10-10T08:01:00Z", "user", "Build the feature"),
            self.message("2026-10-10T08:02:00Z", "assistant", "Built the feature"),
            self.message("2026-10-10T08:03:00Z", "user", "Add coverage"),
        ]
        self.write_history()

    @staticmethod
    def message(timestamp, role, text):
        return {"timestamp": timestamp, "type": "response_item", "payload": {
            "type": "message", "role": role, "content": [{"type": "text", "text": text}]}}

    def write_history(self):
        self.history.write_text("".join(json.dumps(row) + "\n" for row in self.events), encoding="utf-8")

    def cli(self, *args, input_text=None):
        env = os.environ.copy()
        env["CODEX_HOME"] = str(self.home)
        return subprocess.run(
            [sys.executable, str(CLI), "--project", str(self.project), *args],
            input=input_text, text=True, capture_output=True, cwd=self.project, env=env,
        )

    def test_prepare_pages_session_without_writing_json(self):
        first = self.cli("prepare", "--session", SESSION_ID, "--offset", "0", "--limit", "2")
        self.assertEqual(first.returncode, 0, first.stderr)
        page = json.loads(first.stdout)
        self.assertEqual([turn["text"] for turn in page["turns"]], ["Build the feature", "Built the feature"])
        self.assertEqual(page["total_turns"], 3)
        self.assertEqual(page["next_offset"], 2)

        second = self.cli("prepare", "--session", SESSION_ID, "--offset", "2", "--limit", "2")
        self.assertEqual(second.returncode, 0, second.stderr)
        last_page = json.loads(second.stdout)
        self.assertEqual([turn["text"] for turn in last_page["turns"]], ["Add coverage"])
        self.assertIsNone(last_page["next_offset"])
        self.assertEqual(last_page["fingerprint"], page["fingerprint"])
        self.assertFalse((self.project / ".intern101").exists())

    def test_default_prepare_page_is_bounded_for_long_sessions(self):
        for minute in range(4, 29):
            self.events.append(self.message(f"2026-10-10T08:{minute:02d}:00Z", "assistant", f"Update {minute}"))
        self.write_history()
        prepared = self.cli("prepare", "--session", SESSION_ID)
        self.assertEqual(prepared.returncode, 0, prepared.stderr)
        page = json.loads(prepared.stdout)
        self.assertEqual(len(page["turns"]), 10)
        self.assertEqual(page["total_turns"], 28)
        self.assertEqual(page["next_offset"], 10)
        self.assertFalse((self.project / ".intern101").exists())

    def test_save_reads_summary_from_stdin_and_leaves_only_notes(self):
        prepared = self.cli("prepare", "--session", SESSION_ID, "--limit", "2")
        self.assertEqual(prepared.returncode, 0, prepared.stderr)
        fingerprint = json.loads(prepared.stdout)["fingerprint"]
        summary = {"title": "Feature and coverage", "summary": "The feature was built and coverage was requested.",
                   "accomplishments": ["Built the feature"], "decisions": [], "next_steps": ["Add coverage"]}
        saved = self.cli("save", "--session", SESSION_ID, "--expected-fingerprint", fingerprint,
                         "--input", "-", input_text=json.dumps(summary))
        self.assertEqual(saved.returncode, 0, saved.stderr)
        result = json.loads(saved.stdout)
        self.assertEqual(result["status"], "saved")
        self.assertTrue(Path(result["path"]).is_file())
        self.assertTrue((self.project / "chat-contexts" / "INDEX.md").is_file())
        self.assertFalse((self.project / ".intern101").exists())

    def test_save_rejects_changed_session_without_writing_note(self):
        prepared = self.cli("prepare", "--session", SESSION_ID)
        self.assertEqual(prepared.returncode, 0, prepared.stderr)
        fingerprint = json.loads(prepared.stdout)["fingerprint"]
        self.events.append(self.message("2026-10-10T08:04:00Z", "assistant", "Coverage added"))
        self.write_history()
        summary = {"title": "Feature and coverage", "summary": "The feature was built.",
                   "accomplishments": ["Built the feature"], "decisions": [], "next_steps": []}
        saved = self.cli("save", "--session", SESSION_ID, "--expected-fingerprint", fingerprint,
                         "--input", "-", input_text=json.dumps(summary))
        self.assertNotEqual(saved.returncode, 0)
        self.assertIn("changed", saved.stderr.lower())
        self.assertFalse((self.project / "chat-contexts").exists())
        self.assertFalse((self.project / ".intern101").exists())


if __name__ == "__main__":
    unittest.main()
