"""Find today's new Claude Code sessions."""

import sys
import json
import argparse
import re
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))
from lib.utils import get_chat_contexts_dir, get_claude_dir
from lib.session import list_todays_jsonl


def _get_known_session_ids(ctx_dir: Path) -> set:
    known = set()
    if not ctx_dir.exists():
        return known
    uuid_re = re.compile(r'session_id:\s*([a-f0-9-]{36})')
    for md in ctx_dir.glob("*.md"):
        try:
            content = md.read_text(encoding="utf-8", errors="replace")[:600]
            m = uuid_re.search(content)
            if m:
                known.add(m.group(1))
        except OSError:
            pass
    return known


def main():
    claude_dir = get_claude_dir()
    cwd = Path.cwd()
    ctx_dir = get_chat_contexts_dir(cwd)
    known_ids = _get_known_session_ids(ctx_dir)

    jsonl_files = list_todays_jsonl(claude_dir, cwd)
    uuid_re = re.compile(r'^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$')

    results = []
    for f in jsonl_files:
        stem = f.stem
        if not uuid_re.match(stem):
            continue
        if stem in known_ids:
            continue
        stat = f.stat()
        size_kb = round(stat.st_size / 1024)
        mtime = datetime.fromtimestamp(stat.st_mtime).strftime("%H:%M")
        results.append({"path": str(f), "uuid": stem, "mtime": mtime, "size_kb": size_kb})

    results.sort(key=lambda x: x["mtime"])
    print(json.dumps(results))


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"ERROR:{e}", file=sys.stderr)
        sys.exit(1)
