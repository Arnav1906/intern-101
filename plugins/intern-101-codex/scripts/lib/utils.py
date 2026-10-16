"""Cross-platform path resolution and file I/O utilities for intern-101 scripts."""

import os
import sys
from datetime import datetime
from pathlib import Path

IS_WINDOWS = sys.platform == "win32"
IS_MACOS = sys.platform == "darwin"
IS_LINUX = sys.platform.startswith("linux")


def get_plugin_root() -> Path:
    return Path(__file__).resolve().parent.parent.parent


def get_home_dir() -> Path:
    home = os.environ.get("HOME") or os.environ.get("USERPROFILE") or ""
    if home.strip():
        return Path(home.strip())
    return Path.home()


def get_history_home() -> Path:
    from .workspace import project_root, codex_home
    return codex_home(project_root(Path.cwd()))


def get_projects_dir(cwd: Path) -> Path:
    return cwd / "projects"


def get_chat_contexts_dir(cwd: Path) -> Path:
    from .workspace import config, contexts_dir, project_root
    root = project_root(cwd)
    if config(root).get("contexts_dir") is not None:
        return contexts_dir(root)
    return Path(cwd) / "chat-contexts"


def ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def read_file(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except (FileNotFoundError, OSError):
        return ""


def write_file(path: Path, content: str) -> None:
    ensure_dir(path.parent)
    path.write_text(content, encoding="utf-8")


def today_str() -> str:
    return datetime.now().strftime("%Y-%m-%d")


def now_str() -> str:
    return datetime.now().strftime("%Y-%m-%d-%H-%M")
