"""Show all sessions from INDEX.md and optionally search."""

import sys
import argparse
import re
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from lib.utils import get_chat_contexts_dir, read_file
from lib.session import parse_index_rows


def _search_content(ctx_dir: Path, query: str) -> None:
    q = query.lower()
    results = []
    for f in sorted(ctx_dir.glob("*.md")):
        if f.name == "INDEX.md":
            continue
        try:
            text = f.read_text(encoding="utf-8", errors="replace")[:3000]
        except OSError:
            continue
        if q not in text.lower():
            continue
        m_title = re.search(r'^# (.+)$', text, re.MULTILINE)
        title = m_title.group(1).strip() if m_title else f.name
        snippet_m = re.search(r'.{0,60}' + re.escape(q) + r'.{0,60}', text, re.IGNORECASE)
        snippet = snippet_m.group(0).strip() if snippet_m else ""
        results.append(f"{f.name} | {title} | ...{snippet}...")
    print("\n".join(results) if results else "NONE")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--query", "-q", default=None)
    parser.add_argument("--content", action="store_true")
    args = parser.parse_args()

    ctx_dir = get_chat_contexts_dir(Path.cwd())
    if not ctx_dir.is_dir():
        print("NONE")
        sys.exit(0)

    idx_path = ctx_dir / "INDEX.md"
    if not idx_path.is_file():
        print("NONE")
        sys.exit(0)

    rows = list(reversed(parse_index_rows(idx_path)))  # newest-first
    if not rows:
        print("NONE")
        sys.exit(0)

    if args.content and args.query:
        _search_content(ctx_dir, args.query)
        return

    if args.query:
        q = args.query.lower()
        rows = [r for r in rows if q in r["title"].lower() or q in r["filename"].lower()]
        if not rows:
            print("NONE")
            return

    for row in rows:
        summary = row.get("summary", "")
        print(f"{row['date']} | {row['title']} | {row['filename']} | {summary}")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"ERROR:{e}", file=sys.stderr)
        sys.exit(1)
