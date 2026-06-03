import json
import subprocess
import sys
from pathlib import Path

EXTRACTOR = Path("scripts/chat_context_extractor.py")


def _make_jsonl(tmp_path: Path) -> Path:
    p = tmp_path / "abc123.jsonl"
    lines = [
        '{"type":"human","message":{"role":"user","content":"fix the login bug"}}',
        '{"type":"assistant","message":{"role":"assistant","content":[{"type":"text","text":"Sure, I will fix it."},{"type":"tool_use","name":"Edit","input":{"file_path":"src/auth.py"}}]}}',
    ]
    p.write_text("\n".join(lines), encoding="utf-8")
    return p


def test_outputs_valid_json(tmp_path):
    jsonl = _make_jsonl(tmp_path)
    result = subprocess.run(
        [sys.executable, str(EXTRACTOR), str(jsonl)],
        capture_output=True, text=True
    )
    assert result.returncode == 0, result.stderr
    data = json.loads(result.stdout.strip())
    assert data["session_id"] == "abc123"
    assert data["title"] == "fix the login bug"
    assert "src/auth.py" in data["files_modified"]
    assert "transcript" in data
    assert len(data["transcript"]) > 0


def test_error_on_missing_file(tmp_path):
    result = subprocess.run(
        [sys.executable, str(EXTRACTOR), str(tmp_path / "nonexistent.jsonl")],
        capture_output=True, text=True
    )
    assert result.returncode != 0
    assert "ERROR" in result.stderr


def test_transcript_truncated_to_6000_chars(tmp_path):
    p = tmp_path / "long123.jsonl"
    long_msg = "x" * 10000
    p.write_text(
        '{' + f'"type":"human","message":{{"role":"user","content":"{long_msg}"}}' + '}\n',
        encoding="utf-8"
    )
    result = subprocess.run(
        [sys.executable, str(EXTRACTOR), str(p)],
        capture_output=True, text=True
    )
    assert result.returncode == 0
    data = json.loads(result.stdout.strip())
    assert len(data["transcript"]) <= 6100
