"""Show recent sessions and optionally search INDEX.md and file bodies."""

import sys
import argparse
import re
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / 'lib'))

from lib.utils import get_chat_contexts_dir, read_file
from lib.session import parse_index_rows


def _recent_files(ctx_dir: Path, n: int = 5) -> list[Path]:
    files = [
        f for f in ctx_dir.glob("*.md")
        if f.name != "INDEX.md"
    ]
    files.sort(key=lambda f: f.stat().st_mtime, reverse=True)
    return files[:n]


def _title_from_file(text: str, filename: str) -> str:
    m = re.search(r'^# (.+)$', text, re.MULTILINE)
    return m.group(1).strip() if m else filename


def _date_from_file(text: str, filename: str) -> str:
    m = re.search(r'date:\s*(\S+)', text)
    if m:
        return m.group(1)
    return filename[:10]


def show_recent(ctx_dir: Path) -> None:
    files = _recent_files(ctx_dir)
    if not files:
        print("NONE")
        return
    for f in files:
        text = read_file(f)[:600]
        title = _title_from_file(text, f.name)
        date = _date_from_file(text, f.name)
        print(f"{date} | {title} | {f.name}")


def search_index(ctx_dir: Path, query: str) -> None:
    idx = ctx_dir / "INDEX.md"
    if not idx.is_file():
        print("NONE")
        return
    rows = parse_index_rows(idx)
    q = query.lower()
    matches = [r for r in rows if q in r["title"].lower() or q in r["filename"].lower()]
    if not matches:
        print("NONE")
        return
    for r in matches:
        print(f"{r['date']} | {r['title']} | {r['filename']} | ")


def search_content(ctx_dir: Path, query: str) -> None:
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
    parser.add_argument("--query", "-q", default=None, help="search query for INDEX titles")
    parser.add_argument("--content", action="store_true", help="search inside file bodies")
    args = parser.parse_args()

    ctx_dir = get_chat_contexts_dir(Path.cwd())
    if not ctx_dir.is_dir():
        print("NONE")
        sys.exit(0)

    # Always show recent
    show_recent(ctx_dir)

    if args.query and args.content:
        search_content(ctx_dir, args.query)
    elif args.query:
        search_index(ctx_dir, args.query)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"ERROR:{e}", file=sys.stderr)
        sys.exit(1)
