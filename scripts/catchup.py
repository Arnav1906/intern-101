import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / 'lib'))

from lib.utils import get_chat_contexts_dir
from lib.session import parse_index_rows

try:
    cwd = Path.cwd()
    idx_path = get_chat_contexts_dir(cwd) / "INDEX.md"
    if not idx_path.is_file():
        print("NONE")
        sys.exit(0)
    rows = parse_index_rows(idx_path)
    if not rows:
        print("NONE")
        sys.exit(0)
    for row in rows[-5:]:
        date = row["date"]
        title = row["title"]
        filename = row["filename"]
        if filename:
            print(f"{date} | {title} | {filename}")
except Exception as e:
    print(f"ERROR:{e}", file=sys.stderr)
    sys.exit(1)
