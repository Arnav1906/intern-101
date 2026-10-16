"""Session and context file operations for intern-101 skills."""

import re
from pathlib import Path

from .utils import read_file, today_str
from .history_adapter import list_todays_jsonl


def parse_index_rows(index_path: Path) -> list[dict]:
    content = read_file(index_path)
    rows = []
    for line in content.splitlines():
        line = line.strip()
        if not line.startswith("|") or not line.endswith("|"):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if len(cells) < 3:
            continue
        date, title, filename = cells[0], cells[1], cells[2]
        summary = cells[3] if len(cells) > 3 else ""
        # skip header and separator rows
        if not date or set(date) <= {"-", " "}:
            continue
        if not re.match(r"\d{4}-\d{2}-\d{2}", date):
            continue
        filename = filename.strip("`").strip()
        rows.append({"date": date, "title": title, "filename": filename, "summary": summary})
    return rows


def _extract_section(content: str, heading: str) -> str:
    lines = content.splitlines()
    inside = False
    result = []
    for line in lines:
        if line.strip().lower() == f"## {heading.lower()}":
            inside = True
            continue
        if inside:
            if line.startswith("## "):
                break
            result.append(line)
    return "\n".join(result).strip()


def read_session_summary(context_path: Path) -> str:
    return _extract_section(read_file(context_path), "Summary")


def read_session_decisions(context_path: Path) -> str:
    return _extract_section(read_file(context_path), "Key Decisions & Findings")


def list_todays_extracted(contexts_dir: Path) -> list[str]:
    if not contexts_dir.exists():
        return []
    today = today_str()
    return [
        p.name
        for p in contexts_dir.iterdir()
        if p.is_file() and p.name.startswith(today) and p.suffix == ".md"
    ]


def slugify(text: str) -> str:
    text = text.lower().strip()
    text = text.replace(" ", "-")
    text = re.sub(r"[^a-z0-9-]", "", text)
    text = re.sub(r"-+", "-", text)
    return text[:50].rstrip("-")
