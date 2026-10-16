"""Bootstrap helper for project-index-manager skill."""
import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from lib.utils import get_plugin_root, ensure_dir

FIND_PROJECT_DIR_SRC = '''\
import os, sys

def find_project_dir(cwd=None):
    cwd = cwd or os.getcwd()
    def path_to_hash(p):
        if sys.platform == "win32":
            h = p.replace(":\\\\", "--").replace("\\\\", "-").replace("/", "-")
            if h: h = h[0].lower() + h[1:]
        else:
            h = p.replace("/", "-")
        return h
    hash_try = path_to_hash(cwd)
    claude_projects = os.path.join(os.path.expanduser("~"), ".claude", "projects")
    for attempt in [hash_try, hash_try.lower()]:
        d = os.path.join(claude_projects, attempt)
        if os.path.isdir(d):
            return d
    last = os.path.basename(cwd).lower().replace("_", "-")
    for name in os.listdir(claude_projects):
        if name.lower().endswith(last):
            return os.path.join(claude_projects, name)
    return None

if __name__ == "__main__":
    d = find_project_dir()
    if not d:
        print("ERROR: could not find project session dir for: " + os.getcwd())
        sys.exit(1)
    print(d)
'''


def bootstrap():
    helper_dir = Path('.intern101')
    helper_path = helper_dir / 'find_project_dir.py'
    if helper_path.exists():
        print('bootstrapped')
        return
    ensure_dir(helper_dir)
    helper_path.write_text(FIND_PROJECT_DIR_SRC, encoding='utf-8')
    print('bootstrapped')


if __name__ == '__main__':
    bootstrap()
