import json
import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).parent.parent / "scripts" / "chat_context_extractor.py"
PYTHON = sys.executable


def _make_jsonl(tmp_path: Path, entries: list) -> Path:
    p = tmp_path / "session.jsonl"
    p.write_text("\n".join(json.dumps(e) for e in entries), encoding="utf-8")
    return p


def _run(jsonl_path: Path) -> dict:
    result = subprocess.run(
        [PYTHON, str(SCRIPT), str(jsonl_path)],
        capture_output=True, text=True
    )
    assert result.returncode == 0, f"stderr: {result.stderr}"
    lines = [l for l in result.stdout.strip().splitlines() if l.strip()]
    return json.loads(lines[-1])


def _user_msg(text: str, ts: str = "2026-07-08T10:00:00Z") -> dict:
    return {
        "type": "user",
        "timestamp": ts,
        "sessionId": "abc123",
        "message": {"role": "user", "content": text},
    }


def _assistant_msg(text: str, ts: str = "2026-07-08T10:01:00Z") -> dict:
    return {
        "type": "assistant",
        "timestamp": ts,
        "sessionId": "abc123",
        "message": {
            "role": "assistant",
            "model": "claude-sonnet",
            "content": [{"type": "text", "text": text}],
        },
    }


def _assistant_with_tool(prose: str, tool_name: str, tool_input: dict,
                          ts: str = "2026-07-08T10:02:00Z") -> dict:
    return {
        "type": "assistant",
        "timestamp": ts,
        "sessionId": "abc123",
        "message": {
            "role": "assistant",
            "model": "claude-sonnet",
            "content": [
                {"type": "text", "text": prose},
                {"type": "tool_use", "name": tool_name, "input": tool_input},
            ],
        },
    }


def test_skill_injection_filtered(tmp_path):
    """Messages starting with 'Base directory for this skill:' must be excluded."""
    entries = [
        _user_msg("Base directory for this skill: /some/path\n# /catchup — Resume\n## Step 1"),
        _user_msg("What were we working on?"),
        _assistant_msg("We were fixing the extractor."),
    ]
    data = _run(_make_jsonl(tmp_path, entries))
    user_texts = [t["text"] for t in data["turns"] if t["role"] == "user"]
    assert len(user_texts) == 1
    assert user_texts[0] == "What were we working on?"


def test_sidechain_filtered(tmp_path):
    """Entries with isSidechain=True must be excluded."""
    entries = [
        {**_user_msg("Real message"), "isSidechain": False},
        {**_user_msg("Sidechain message"), "isSidechain": True},
        _assistant_msg("Response to real message."),
    ]
    data = _run(_make_jsonl(tmp_path, entries))
    user_texts = [t["text"] for t in data["turns"] if t["role"] == "user"]
    assert len(user_texts) == 1
    assert user_texts[0] == "Real message"


def test_lean_json_schema(tmp_path):
    """Output must contain all required top-level fields."""
    entries = [
        _user_msg("Fix the bug."),
        _assistant_with_tool("Let me check the file.", "Write",
                              {"file_path": "scripts/foo.py", "description": "fix bug"}),
    ]
    data = _run(_make_jsonl(tmp_path, entries))
    for field in ("session_id", "date", "turns", "files_modified",
                  "session_count", "project_root", "total_user", "total_assistant"):
        assert field in data, f"Missing field: {field}"


def test_prose_truncated_at_1200(tmp_path):
    """Assistant prose longer than 1200 chars must be truncated."""
    long_prose = "x" * 2000
    entries = [_user_msg("go"), _assistant_msg(long_prose)]
    data = _run(_make_jsonl(tmp_path, entries))
    assistant_turns = [t for t in data["turns"] if t["role"] == "assistant"]
    assert len(assistant_turns) == 1
    assert len(assistant_turns[0]["text"]) <= 1200


def test_tool_calls_have_no_output(tmp_path):
    """Tool calls appear as description strings in 'tools', never as result output."""
    entries = [
        _user_msg("run it"),
        _assistant_with_tool("Running tests.", "Bash",
                              {"command": "pytest", "description": "Run test suite"}),
    ]
    data = _run(_make_jsonl(tmp_path, entries))
    assistant_turns = [t for t in data["turns"] if t["role"] == "assistant"]
    assert assistant_turns[0]["tools"] == ["Bash: Run test suite"]


def test_files_modified_tracks_writes(tmp_path):
    """files_modified must list paths from Write/Edit tool calls."""
    entries = [
        _user_msg("fix it"),
        _assistant_with_tool("Fixing.", "Write", {"file_path": "scripts/foo.py"}),
        _assistant_with_tool("Also.", "Edit", {"file_path": "scripts/bar.py"}),
    ]
    data = _run(_make_jsonl(tmp_path, entries))
    assert "scripts/foo.py" in data["files_modified"]
    assert "scripts/bar.py" in data["files_modified"]
