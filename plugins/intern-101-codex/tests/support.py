"""Isolated Codex rollout fixtures shared by package workflow tests."""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path

PACKAGE = Path(__file__).resolve().parents[1]

class CodexFixture(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.base = Path(self.temporary.name)
        self.project = self.base / "project with space-\u00e9"
        self.project.mkdir()
        (self.project / ".git").mkdir()
        self.home = self.base / "codex-home"
        self.history = self.home / "sessions" / "rollout.jsonl"
        self.history.parent.mkdir(parents=True)
        self.sid = "11111111-1111-4111-8111-111111111111"
        start = datetime.now().astimezone().replace(hour=9, minute=0, second=0, microsecond=0)
        self.rows = [{"type": "session_meta", "timestamp": start.isoformat(),
                      "payload": {"id": self.sid, "cwd": str(self.project),
                                  "timestamp": start.isoformat()}}]
        for minute in range(1, 29):
            self.rows.append({"type": "response_item",
                              "timestamp": (start + timedelta(minutes=minute)).isoformat(),
                              "payload": {"type": "message",
                                          "role": "user" if minute % 2 else "assistant",
                                          "content": [{"type": "text", "text": f"Conversation {minute}"}]}})
        self.write_history()
        self.env = dict(os.environ, CODEX_HOME=str(self.home),
                        CLAUDE_PLUGIN_ROOT=str(self.base / "unrelated-claude-package"),
                        PYTHONDONTWRITEBYTECODE="1", PYTHONIOENCODING="utf-8")

    def write_history(self):
        self.history.write_text("".join(json.dumps(row) + "\n" for row in self.rows), encoding="utf-8")

    def run_script(self, script, *arguments, cwd=None):
        return subprocess.run([sys.executable, str(PACKAGE / "scripts" / script), *arguments],
                              cwd=cwd or self.project, env=self.env,
                              capture_output=True, text=True, encoding="utf-8")

    def adapter_process(self, function, *arguments):
        code = ("import sys,json; sys.path.insert(0,sys.argv[1]); "
                "from lib import history_adapter; "
                "result=getattr(history_adapter,sys.argv[2])(*json.loads(sys.argv[3])); "
                "print(json.dumps(result,default=str))")
        return subprocess.run([sys.executable, "-c", code, str(PACKAGE / "scripts"),
                               function, json.dumps(arguments)], cwd=self.project,
                              env=self.env, capture_output=True, text=True, encoding="utf-8")

    def adapter(self, function, *arguments):
        process = self.adapter_process(function, *arguments)
        self.assertEqual(process.returncode, 0, process.stderr)
        return json.loads(process.stdout)
