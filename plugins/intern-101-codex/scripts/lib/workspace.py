"""Resolve project configuration without depending on the plugin cache location."""

import json
import os
from pathlib import Path


def project_root(path=None):
    start = Path(path or Path.cwd()).expanduser().resolve()
    if not start.is_dir():
        raise ValueError("Project directory does not exist: {}".format(start))
    # A project configuration takes priority over a surrounding monorepo.
    for folder in (start, *start.parents):
        if (folder / ".intern101" / "config.json").is_file():
            return folder
        if (folder / ".git").exists():
            return folder
    return start


def config(root):
    path = root / ".intern101" / "config.json"
    if not path.exists():
        return {}
    value = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(value, dict):
        raise ValueError(".intern101/config.json must contain a JSON object")
    return value


def codex_home(root, override=None):
    configured = override or config(root).get("codex_home")
    value = configured if configured and configured != "auto" else os.environ.get("CODEX_HOME")
    if not value:
        return Path.home() / ".codex"
    path = Path(value).expanduser()
    return (root / path).resolve() if not path.is_absolute() else path.resolve()


def inside(root, path):
    resolved = Path(path).resolve()
    try:
        resolved.relative_to(root.resolve())
    except ValueError:
        raise ValueError("Path is outside the project: {}".format(path))
    return resolved


def contexts_dir(root):
    value = config(root).get("contexts_dir", "chat-contexts")
    if not isinstance(value, str) or not value.strip():
        raise ValueError("contexts_dir must be a non-empty path")
    return inside(root, root / value)


def belongs_to_project(cwd, root):
    if not cwd:
        return False
    return Path(cwd).expanduser().resolve() == root or root in Path(cwd).expanduser().resolve().parents
