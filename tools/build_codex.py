"""Build an independently installable Codex-only package using the standard library."""

import argparse
import json
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile


def build(repository, output):
    plugin = repository / "plugins" / "intern-101-codex"
    manifest = json.loads((plugin / ".codex-plugin" / "plugin.json").read_text(encoding="utf-8"))
    destination = output / "intern-101-codex-{}.zip".format(manifest["version"])
    output.mkdir(parents=True, exist_ok=True)
    files = [plugin / ".codex-plugin" / "plugin.json", plugin / "README.md", plugin / "LICENSE"]
    for directory, extension in (("skills", ".md"), ("references", ".md"), ("scripts", ".py")):
        files.extend(sorted((plugin / directory).rglob("*" + extension)))
    with ZipFile(destination, "w", ZIP_DEFLATED) as archive:
        for path in files:
            archive.write(path, "intern-101-codex/" + path.relative_to(plugin).as_posix())
    return destination


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("dist"))
    args = parser.parse_args()
    print(build(Path(__file__).resolve().parent.parent, args.output.resolve()))
