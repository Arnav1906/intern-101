"""Adapt packaged Codex history to the original complete-session contracts.

All transcript interpretation stays in codex_sessions. Filesystem contracts
require a real rollout: database-only sessions cannot supply paths or sizes.
"""

import re
from datetime import datetime
from pathlib import Path

from .codex_sessions import discover, local_time, metadata, prepare
from .workspace import belongs_to_project, codex_home, contexts_dir, project_root


def runtime(project=None):
    root = project_root(project)
    return root, codex_home(root)


def _select(root, home, source=None):
    if source is not None:
        path = Path(source).expanduser().resolve()
        meta = metadata(path)
        if not belongs_to_project(meta.get("cwd"), root):
            raise ValueError("Session does not belong to the selected project")
        sid = meta.get("id") or meta.get("session_id")
        if not sid:
            raise ValueError("Session metadata has no session ID")
        return {"id": sid, "cwd": meta["cwd"], "path": str(path),
                "history_mode": meta.get("history_mode", "legacy")}
    items = discover(home, root)
    if not items:
        raise ValueError("No matching Codex session found")
    pairs = [(prepare(item, home, root), item) for item in items]
    return max(pairs, key=lambda pair: local_time(pair[0]["last_ts"]))[1]


def _rollout_file(selected):
    value = selected.get("path")
    path = Path(value).expanduser().resolve() if value else None
    if path is None or not path.is_file():
        raise ValueError(
            "No usable Codex rollout file for session {}. Database-only history "
            "cannot satisfy the required path and file-size contract.".format(selected["id"]))
    return path


def latest_session_path(project=None):
    root, home = runtime(project)
    return str(_rollout_file(_select(root, home)))


def clean_session(source=None, project=None):
    root, home = runtime(project)
    data = prepare(_select(root, home, source), home, root)
    first = local_time(data["first_ts"])
    result = {key: data[key] for key in (
        "session_id", "model", "first_ts", "last_ts", "turns", "files_modified",
        "project_root", "total_user", "total_assistant",
    )}
    result.update(custom_title="", date=first.strftime("%Y-%m-%d"), session_count=1)
    return result


def known_session_ids(folder):
    pattern = re.compile(r"^session_id:\s*[\"']?([0-9a-fA-F-]{36})", re.MULTILINE)
    known = set()
    for path in Path(folder).rglob("*.md"):
        known.update(pattern.findall(path.read_text(encoding="utf-8-sig")))
    return known


def _today_rollouts(home, root):
    today = datetime.now().astimezone().strftime("%Y-%m-%d")
    for selected in discover(home, root):
        data = prepare(selected, home, root)
        if today in data["activity_dates"]:
            yield selected, _rollout_file(selected)


def todays_new_sessions(project=None):
    root, home = runtime(project)
    known = known_session_ids(contexts_dir(root))
    rows = []
    for selected, path in _today_rollouts(home, root):
        if selected["id"] in known:
            continue
        stat = path.stat()
        rows.append({"path": str(path), "uuid": selected["id"],
                     "mtime": datetime.fromtimestamp(stat.st_mtime).strftime("%H:%M"),
                     "size_kb": round(stat.st_size / 1024)})
    return sorted(rows, key=lambda row: row["mtime"])


def list_todays_jsonl(home, cwd):
    root = project_root(cwd)
    home = Path(home).expanduser().resolve()
    return [path for _, path in _today_rollouts(home, root)]
