"""Bootstrap the original project-local history compatibility helper."""
import sys
from pathlib import Path

if __name__ == "__main__":
    package_scripts = Path(__file__).resolve().parent
    helper = Path.cwd() / ".intern101" / "find_project_dir.py"
    if not helper.exists():
        helper.parent.mkdir(parents=True, exist_ok=True)
        text = (
            "import sys\nfrom pathlib import Path\n"
            f"sys.path.insert(0, {str(package_scripts)!r})\n"
            "from lib.history_adapter import latest_session_path\n\n"
            "def find_project_dir(cwd=None):\n"
            "    return str(Path(latest_session_path(project=cwd)).parent)\n"
        )
        helper.write_text(text, encoding="utf-8")
    print("bootstrapped")
