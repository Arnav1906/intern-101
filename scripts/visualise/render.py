"""Step 6-7 of /visualise: copy graph-template.html → visualise-out/graph.html (template is verbatim, loads graph.json at runtime)."""

import sys
import os
import argparse
import shutil
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / 'lib'))

# The template lives alongside the SKILL.md in the plugin assets
TEMPLATE_RELATIVE = Path("plugins") / "visualise" / "assets" / "graph-template.html"


def _find_template(cwd: Path) -> Path | None:
    # try plugin root env var first, then search from cwd upward
    plugin_root = Path(
        os.environ.get("CLAUDE_PLUGIN_ROOT", "")
    ).resolve() if os.environ.get("CLAUDE_PLUGIN_ROOT") else None

    if plugin_root and (plugin_root / "plugins" / "visualise" / "assets" / "graph-template.html").exists():
        return plugin_root / "plugins" / "visualise" / "assets" / "graph-template.html"

    # try relative to this script's grandparent (plugin root)
    script_plugin_root = Path(__file__).resolve().parent.parent.parent
    candidate = script_plugin_root / "plugins" / "visualise" / "assets" / "graph-template.html"
    if candidate.exists():
        return candidate

    # try from cwd
    candidate2 = cwd / TEMPLATE_RELATIVE
    if candidate2.exists():
        return candidate2

    return None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("target", nargs="?", default="", help="target directory (default: cwd)")
    args = parser.parse_args()

    cwd = Path.cwd()
    raw_target = args.target.strip()
    target = (cwd / raw_target).resolve() if raw_target else cwd.resolve()
    out_dir = target / 'visualise-out'

    if not (out_dir / 'graph.json').exists():
        print(f"ERROR:graph.json not found in {out_dir} — run cluster.py first", file=sys.stderr)
        sys.exit(1)

    template = _find_template(cwd)
    if not template:
        print(f"ERROR:graph-template.html not found", file=sys.stderr)
        sys.exit(1)

    dest = out_dir / 'graph.html'
    shutil.copy2(template, dest)
    print(f"WRITTEN:{dest}")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"ERROR:{e}", file=sys.stderr)
        sys.exit(1)
