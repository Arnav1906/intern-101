import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from zipfile import ZipFile

REPO = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("build_codex", REPO / "tools" / "build_codex.py")
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)


class PackageTests(unittest.TestCase):
    def test_release_is_self_contained_and_contains_only_codex_runtime(self):
        with tempfile.TemporaryDirectory() as tmp:
            archive = builder.build(REPO, Path(tmp))
            with ZipFile(archive) as package:
                names = package.namelist()
                self.assertTrue(all(name.startswith("intern-101-codex/") for name in names))
                self.assertFalse(any(".claude" in name or "/tests/" in name or "__pycache__" in name for name in names))
                manifest = json.loads(package.read("intern-101-codex/.codex-plugin/plugin.json"))
                self.assertEqual(manifest["skills"], "./skills/")
                self.assertEqual(manifest["hooks"], {})
                self.assertEqual(len([name for name in names if name.endswith("/SKILL.md")]), 9)
                package.extractall(Path(tmp) / "installed")
                import subprocess
                import sys
                helper = Path(tmp) / "installed" / "intern-101-codex" / "scripts" / "intern101.py"
                project = Path(tmp) / "fresh-project"
                project.mkdir()
                result = subprocess.run([sys.executable, str(helper), "--project", str(project), "catchup"],
                                        capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(json.loads(result.stdout), {"sessions": []})


if __name__ == "__main__":
    unittest.main()
