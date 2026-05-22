"""Collect today's (or yesterday's) chat-context summaries for the daily update skill."""

import sys
import argparse
import re
from pathlib import Path
from datetime import datetime, timedelta

sys.path.insert(0, str(Path(__file__).parent / 'lib'))

from lib.utils import get_chat_contexts_dir


def _extract_sections(text: str, *headings: str) -> list[tuple[str, str]]:
    results = []
    for heading in headings:
        pattern = re.compile(
            re.escape(f"## {heading}") + r'\n(.*?)(?=\n## |\Z)',
            re.DOTALL | re.IGNORECASE,
        )
        m = pattern.search(text)
        if m:
            results.append((heading, m.group(1).strip()))
    return results


def _title(text: str, filename: str) -> str:
    m = re.search(r'^# (.+)$', text, re.MULTILINE)
    return m.group(1).strip() if m else filename


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--yesterday", action="store_true", help="use yesterday's sessions")
    args = parser.parse_args()

    if args.yesterday:
        target_date = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    else:
        target_date = datetime.now().strftime("%Y-%m-%d")

    ctx_dir = get_chat_contexts_dir(Path.cwd())
    if not ctx_dir.is_dir():
        print("NONE")
        sys.exit(0)

    files = sorted([
        f for f in ctx_dir.glob("*.md")
        if f.name.startswith(target_date) and f.name != "INDEX.md"
    ])

    if not files:
        print("NONE")
        sys.exit(0)

    # Print filenames first so the SKILL.md flow can present them
    print(f"FILES:{len(files)}")
    for f in files:
        print(f"FILE:{f}")

    # Then print extracted content
    for f in files:
        try:
            text = f.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        title = _title(text, f.name)
        print(f"\n=== {title} ===")
        sections = _extract_sections(text, "Summary", "Key Topics", "Key Decisions & Findings")
        for heading, content in sections:
            print(f"## {heading}")
            print(content)
        print()


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"ERROR:{e}", file=sys.stderr)
        sys.exit(1)
