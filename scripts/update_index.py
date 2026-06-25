"""Append a 4-column row to chat-contexts/INDEX.md."""

import sys
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from lib.utils import get_chat_contexts_dir, write_file


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", required=True)
    parser.add_argument("--title", required=True)
    parser.add_argument("--filename", required=True)
    parser.add_argument("--summary", required=True)
    args = parser.parse_args()

    ctx_dir = get_chat_contexts_dir(Path.cwd())
    idx_path = ctx_dir / "INDEX.md"
    title = args.title[:80].replace("|", "-")
    summary = args.summary[:120].replace("|", "-")
    row = f"| {args.date} | {title} | `{args.filename}` | {summary} |"

    if not idx_path.exists():
        header = "| Date | Title | Filename | Summary |\n|---|---|---|---|\n"
        write_file(idx_path, header + row + "\n")
    else:
        content = idx_path.read_text(encoding="utf-8")
        if f"`{args.filename}`" not in content:
            write_file(idx_path, content.rstrip() + "\n" + row + "\n")

    print(f"INDEXED:{args.filename}")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"ERROR:{e}", file=sys.stderr)
        sys.exit(1)
