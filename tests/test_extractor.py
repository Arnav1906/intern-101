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


# ── Catchup merger tests ────────────────────────────────────────────────────

CATCHUP = Path(__file__).parent.parent / "scripts" / "catchup.py"


def _write_index(directory: Path, rows: list) -> None:
    """Write a chat-contexts/INDEX.md with the given rows."""
    ctx = directory / "chat-contexts"
    ctx.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Chat Context Index\n",
        "| Date | Title | File | First Accomplishment |\n",
        "|------|-------|------|---------------------|\n",
    ]
    for date, title, filename in rows:
        lines.append("| {} | {} | `{}` | bullet |\n".format(date, title, filename))
    (ctx / "INDEX.md").write_text("".join(lines), encoding="utf-8")


def _run_catchup(cwd: Path) -> list:
    result = subprocess.run(
        [PYTHON, str(CATCHUP)],
        capture_output=True, text=True, cwd=str(cwd)
    )
    output = result.stdout.strip()
    if output == "NONE" or not output:
        return []
    return [line for line in output.splitlines() if line.strip()]


def test_catchup_returns_none_when_no_index(tmp_path):
    lines = _run_catchup(tmp_path)
    assert lines == []


def test_catchup_reads_cwd_index(tmp_path):
    _write_index(tmp_path, [("2026-07-01", "Session A", "2026-07-01-a.md")])
    lines = _run_catchup(tmp_path)
    assert len(lines) == 1
    assert "Session A" in lines[0]


def test_catchup_merges_and_deduplicates(tmp_path):
    # CWD index
    _write_index(tmp_path, [
        ("2026-07-01", "Session A", "2026-07-01-a.md"),
        ("2026-07-03", "Session C", "2026-07-03-c.md"),
    ])
    # Git root index (simulate via a parent dir with .git marker)
    git_root = tmp_path / "project"
    git_root.mkdir()
    (git_root / ".git").mkdir()
    _write_index(git_root, [
        ("2026-07-01", "Session A", "2026-07-01-a.md"),  # duplicate
        ("2026-07-02", "Session B", "2026-07-02-b.md"),  # additive
    ])
    # Run catchup from a subdirectory of git_root, so CWD != git_root
    sub = git_root / "src"
    sub.mkdir()
    # Also put CWD index in sub (simulating CWD chat-contexts)
    _write_index(sub, [("2026-07-03", "Session C", "2026-07-03-c.md")])

    lines = _run_catchup(sub)
    # Should have A + B + C without duplicate A
    titles = [l.split("|")[1].strip() for l in lines]
    assert len(titles) == len(set(titles)), "Duplicates found: {}".format(titles)


def test_catchup_sorted_newest_first(tmp_path):
    _write_index(tmp_path, [
        ("2026-06-01", "Old Session", "2026-06-01-old.md"),
        ("2026-07-05", "New Session", "2026-07-05-new.md"),
        ("2026-06-15", "Mid Session", "2026-06-15-mid.md"),
    ])
    lines = _run_catchup(tmp_path)
    dates = [l.split("|")[0].strip() for l in lines]
    assert dates == sorted(dates, reverse=True), "Not sorted newest-first: {}".format(dates)
