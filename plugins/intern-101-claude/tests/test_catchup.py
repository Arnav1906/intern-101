"""Catchup lists saved notes without redirecting to extraction."""
import os
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / 'scripts' / 'catchup.py'


class CatchupTests(unittest.TestCase):
    def test_saved_note_list_ignores_unextracted_today_session(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            project = base / 'sample-project'
            project.mkdir()
            (project / '.git').mkdir()
            folder = project / 'chat-contexts'
            folder.mkdir()
            previous_date = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
            (folder / 'INDEX.md').write_text(
                '| Date | Title | File | Summary |\n| --- | --- | --- | --- |\n'
                f'| {previous_date} | Saved work | `saved.md` | Continue work |\n', encoding='utf-8')
            slug = (str(project.resolve()).replace('\\', '/').replace(':', '-').replace('/', '-')
                    .replace("'", '').replace(' ', '-').replace('_', '-').lstrip('-'))
            history = base / '.claude' / 'projects' / slug
            history.mkdir(parents=True)
            (history / '11111111-1111-4111-8111-111111111111.jsonl').write_text('{}\n', encoding='utf-8')
            env = dict(os.environ, HOME=str(base), USERPROFILE=str(base), PYTHONDONTWRITEBYTECODE='1')
            probe = subprocess.run(
                [sys.executable, '-c', 'import sys; from pathlib import Path; sys.path.insert(0, sys.argv[1]); from lib.session import list_todays_jsonl; from lib.utils import get_claude_dir; print(list_todays_jsonl(get_claude_dir(), Path.cwd()))', str(SCRIPT.parent)],
                cwd=project, env=env, capture_output=True, text=True, encoding='utf-8')
            self.assertEqual(probe.returncode, 0, probe.stderr)
            self.assertIn('11111111-1111-4111-8111-111111111111', probe.stdout)
            result = subprocess.run([sys.executable, str(SCRIPT)], cwd=project, env=env,
                                    capture_output=True, text=True, encoding='utf-8')
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout.strip(), f'{previous_date} | Saved work | saved.md | Continue work')


if __name__ == '__main__':
    unittest.main()
