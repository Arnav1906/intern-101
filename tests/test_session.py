import pytest
from pathlib import Path
from scripts.lib.session import parse_index_rows


def _make_index(tmp_path: Path, content: str) -> Path:
    p = tmp_path / "INDEX.md"
    p.write_text(content, encoding="utf-8")
    return p


def test_parses_3_column_row(tmp_path):
    idx = _make_index(tmp_path, (
        "| Date | Title | Filename |\n"
        "|---|---|---|\n"
        "| 2026-06-03 | My session | `2026-06-03_my-session.md` |\n"
    ))
    rows = parse_index_rows(idx)
    assert len(rows) == 1
    assert rows[0]["date"] == "2026-06-03"
    assert rows[0]["title"] == "My session"
    assert rows[0]["filename"] == "2026-06-03_my-session.md"
    assert rows[0]["summary"] == ""


def test_parses_4_column_row(tmp_path):
    idx = _make_index(tmp_path, (
        "| Date | Title | Filename | Summary |\n"
        "|---|---|---|---|\n"
        "| 2026-06-03 | My session | `2026-06-03_my-session.md` | Worked on refactor. |\n"
    ))
    rows = parse_index_rows(idx)
    assert len(rows) == 1
    assert rows[0]["summary"] == "Worked on refactor."


def test_skips_header_and_separator(tmp_path):
    idx = _make_index(tmp_path, (
        "| Date | Title | Filename | Summary |\n"
        "|---|---|---|---|\n"
        "| 2026-06-03 | A | `a.md` | Summary A |\n"
        "| 2026-06-02 | B | `b.md` | Summary B |\n"
    ))
    rows = parse_index_rows(idx)
    assert len(rows) == 2


def test_empty_index_returns_empty(tmp_path):
    idx = _make_index(tmp_path, "| Date | Title | Filename |\n|---|---|---|\n")
    assert parse_index_rows(idx) == []
