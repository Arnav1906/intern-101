import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from lib.utils import get_chat_contexts_dir
from lib.session import parse_index_rows


def _find_git_root(start):
    """Walk up from start to find the nearest directory containing .git."""
    current = Path(start).resolve()
    while True:
        if (current / ".git").exists():
            return current
        parent = current.parent
        if parent == current:
            return None
        current = parent


def _load_index(idx_path):
    if not idx_path.is_file():
        return []
    return parse_index_rows(idx_path)


try:
    cwd = Path.cwd()

    # Primary: project root chat-contexts (git root, or CWD if no git root found)
    git_root = _find_git_root(cwd)
    primary_dir = git_root if git_root else cwd
    primary_idx = get_chat_contexts_dir(primary_dir) / "INDEX.md"
    primary_rows = _load_index(primary_idx)

    # Secondary: CWD chat-contexts (additive when CWD differs from primary_dir)
    secondary_rows = []
    if cwd.resolve() != primary_dir.resolve():
        cwd_idx = get_chat_contexts_dir(cwd) / "INDEX.md"
        if cwd_idx.resolve() != primary_idx.resolve():
            secondary_rows = _load_index(cwd_idx)

    # Merge: primary first, then additive secondary rows
    seen = {r["filename"] for r in primary_rows}
    merged = list(primary_rows)
    for row in secondary_rows:
        if row["filename"] not in seen:
            merged.append(row)
            seen.add(row["filename"])

    # Sort newest-first; take up to 5 most recent
    merged.sort(key=lambda r: r["date"], reverse=True)

    if not merged:
        print("NONE")
        sys.exit(0)

    for row in merged[:5]:
        if row["filename"]:
            print("{} | {} | {}".format(row["date"], row["title"], row["filename"]))

except Exception as e:
    print("ERROR:{}".format(e), file=sys.stderr)
    sys.exit(1)
