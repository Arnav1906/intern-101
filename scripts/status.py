"""Collect sub-project status from projects/*/_progress.md files."""

import sys
import json
import re
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / 'lib'))

from lib.utils import get_projects_dir, read_file


def _extract_status(text: str) -> str:
    m = re.search(r'## Status:\s*(.+)', text)
    return m.group(1).strip() if m else "UNKNOWN"


def _extract_pending(text: str) -> list:
    return re.findall(r'- \[ \] (.+)', text)


def _extract_done(text: str) -> list:
    return re.findall(r'- \[x\] (.+)', text, re.IGNORECASE)


def _extract_gotcha(text: str) -> str:
    m = re.search(r'## Key Gotcha\n(.+?)(?=\n## |\Z)', text, re.DOTALL)
    return m.group(1).strip()[:120] if m else ""


def main():
    cwd = Path.cwd()
    projects_dir = get_projects_dir(cwd)
    if not projects_dir.is_dir():
        print("NONE")
        sys.exit(0)

    results = []
    for progress_file in sorted(projects_dir.glob("*/*_progress.md")):
        text = read_file(progress_file)
        name = progress_file.parent.name
        pending = _extract_pending(text)
        done = _extract_done(text)
        results.append({
            "name": name,
            "status": _extract_status(text),
            "done": len(done),
            "pending": len(pending),
            "next": pending[0].strip() if pending else "",
            "gotcha": _extract_gotcha(text),
            "file": str(progress_file),
        })

    print(json.dumps(results))


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"ERROR:{e}", file=sys.stderr)
        sys.exit(1)
