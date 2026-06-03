import subprocess
import sys
from pathlib import Path


def _setup(tmp_path: Path) -> None:
    ctx = tmp_path / "chat-contexts"
    ctx.mkdir()
    (ctx / "INDEX.md").write_text(
        "| Date | Title | Filename | Summary |\n"
        "|---|---|---|---|\n"
        "| 2026-06-01 | Session A | `2026-06-01_a.md` | Did thing A. |\n"
        "| 2026-06-02 | Session B | `2026-06-02_b.md` | Did thing B. |\n"
        "| 2026-06-03 | Session C | `2026-06-03_c.md` | Did thing C. |\n",
        encoding="utf-8"
    )


_SCRIPT = str(Path(__file__).parent.parent / "scripts" / "recall.py")


def _run_recall(tmp_path: Path, *args) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, _SCRIPT, *args],
        capture_output=True, text=True, cwd=str(tmp_path)
    )


def test_shows_all_sessions_newest_first(tmp_path):
    _setup(tmp_path)
    result = _run_recall(tmp_path)
    assert result.returncode == 0
    lines = [l for l in result.stdout.strip().splitlines() if l.strip()]
    assert len(lines) == 3
    assert "2026-06-03" in lines[0]
    assert "2026-06-01" in lines[2]


def test_query_filters_by_title(tmp_path):
    _setup(tmp_path)
    result = _run_recall(tmp_path, "--query", "Session B")
    assert result.returncode == 0
    lines = [l for l in result.stdout.strip().splitlines() if l.strip()]
    assert any("Session B" in l for l in lines)
    assert not any("Session A" in l for l in lines)


def test_no_index_returns_none(tmp_path):
    result = _run_recall(tmp_path)
    assert "NONE" in result.stdout


def test_summary_included_in_output(tmp_path):
    _setup(tmp_path)
    result = _run_recall(tmp_path)
    assert "Did thing C." in result.stdout
