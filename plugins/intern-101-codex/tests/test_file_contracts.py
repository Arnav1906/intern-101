"""Subprocess contracts for the original file and Git helper interfaces."""
import json
import subprocess
from datetime import datetime, timedelta
from pathlib import Path

from support import CodexFixture, PACKAGE


class FileContracts(CodexFixture):
    def output(self, script, *args, cwd=None):
        result = self.run_script(script, *args, cwd=cwd)
        self.assertEqual(result.returncode, 0, result.stderr)
        return result.stdout.strip()

    def index(self, folder, rows):
        folder.mkdir(parents=True, exist_ok=True)
        (folder / 'INDEX.md').write_text(
            '| Date | Title | File | Summary |\n| --- | --- | --- | --- |\n' +
            ''.join('| {} | {} | `{}` | {} |\n'.format(*r) for r in rows), encoding='utf-8')

    def test_empty_protocols(self):
        self.assertEqual(self.output('recall.py'), 'NONE')
        self.assertEqual(self.output('daily_update.py'), 'NONE')
        self.assertEqual(self.output('status.py'), 'NONE')
        self.assertEqual(self.output('wrap_up.py', '--check'), 'NO_REPO')

    def test_recall_rows_title_filename_and_body_search(self):
        folder = self.project / 'chat-contexts'
        self.index(folder, [('2026-01-01', 'Alpha design', 'first.md', 'First summary'),
                            ('2026-01-02', 'Beta work', 'second.md', 'Second summary')])
        (folder / 'first.md').write_text('# Alpha design\nBody quartz details', encoding='utf-8')
        (folder / 'second.md').write_text('# Beta work\nDifferent text', encoding='utf-8')
        rows = self.output('recall.py').splitlines()
        self.assertEqual(rows, ['2026-01-02 | Beta work | second.md | Second summary',
                                '2026-01-01 | Alpha design | first.md | First summary'])
        self.assertEqual(self.output('recall.py', '--query', 'alpha'), rows[1])
        self.assertEqual(self.output('recall.py', '--query', 'second.md'), rows[0])
        self.assertEqual(self.output('recall.py', '--query', 'quartz'), 'NONE')
        self.assertIn('first.md | Alpha design | ...Body quartz details...',
                      self.output('recall.py', '--query', 'quartz', '--content'))

    def test_status_array_counts_and_gotcha(self):
        folder = self.project / 'projects'
        folder.mkdir()
        self.assertEqual(self.output('status.py'), '[]')
        domain = folder / 'engine'
        domain.mkdir()
        progress = domain / 'engine_progress.md'
        progress.write_text('## Status: In progress\n- [x] Complete\n- [X] Also complete\n'
                            '- [ ] Next action\n- [ ] Later action\n\n## Key Gotcha\n'
                            'Keep the lock.\n\n## Notes\nOther text', encoding='utf-8')
        self.assertEqual(json.loads(self.output('status.py')), [{
            'name': 'engine', 'status': 'In progress', 'done': 2, 'pending': 2,
            'next': 'Next action', 'gotcha': 'Keep the lock.', 'file': str(progress)}])

    def test_catchup_lists_saved_sessions_without_extraction_gate(self):
        nested = self.project / 'nested'
        nested.mkdir()
        rows = [('2026-01-0' + str(n), 'Root ' + str(n), str(n) + '.md', 'root')
                for n in range(1, 5)]
        self.index(self.project / 'chat-contexts', rows)
        self.index(nested / 'chat-contexts', [
            ('2026-01-09', 'Duplicate', '4.md', 'secondary'),
            ('2026-01-08', 'Extra', 'extra.md', 'secondary'),
            ('2026-01-07', 'More', 'more.md', 'secondary')])
        result = self.output('catchup.py', cwd=nested).splitlines()
        self.assertEqual(len(result), 5)
        self.assertEqual(len({r.split(' | ')[2] for r in result}), 5)
        self.assertIn('2026-01-04 | Root 4 | 4.md | root', result)
        self.assertFalse(any('Duplicate' in r for r in result))
        self.history.unlink()
        self.assertEqual(self.output('catchup.py', cwd=nested).splitlines(), result)
        self.write_history()
        today = datetime.now().strftime('%Y-%m-%d')
        self.index(self.project / 'chat-contexts', rows + [(today, 'Today', 'today.md', 'new')])
        self.assertFalse(self.output('catchup.py', cwd=nested).startswith('STALE:'))

    def test_catchup_with_raw_history_but_no_saved_notes_returns_none(self):
        self.assertEqual(self.output('catchup.py'), 'NONE')

    def test_daily_update_today_yesterday_sections(self):
        folder = self.project / 'chat-contexts'
        folder.mkdir()
        for days, args in [(0, ()), (1, ('--yesterday',))]:
            date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
            note = folder / (date + '-note.md')
            note.write_text('# Note ' + str(days) + '\n\n## Summary\nSummary text\n\n'
                            '## Key Topics\nTopic text\n\n## Key Decisions & Findings\n'
                            'Decision text\n\n## Other\nDo not include', encoding='utf-8')
            result = self.output('daily_update.py', *args)
            self.assertTrue(result.startswith('FILES:1\nFILE:' + str(note)))
            for heading, body in [('Summary', 'Summary text'), ('Key Topics', 'Topic text'),
                                  ('Key Decisions & Findings', 'Decision text')]:
                self.assertIn('## ' + heading + '\n' + body, result)
            self.assertNotIn('Do not include', result)

    def test_context_override_and_guard(self):
        config = self.project / '.intern101'
        config.mkdir()
        config_file = config / 'config.json'
        config_file.write_text(json.dumps({'contexts_dir': 'saved/notes'}), encoding='utf-8')
        self.index(self.project / 'saved/notes', [('2026-01-01', 'Override', 'note.md', 'saved')])
        self.assertEqual(self.output('recall.py'), '2026-01-01 | Override | note.md | saved')
        config_file.write_text(json.dumps({'contexts_dir': '../outside'}), encoding='utf-8')
        result = self.run_script('recall.py')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('Path is outside the project', result.stderr)

    def test_runtime_bindings_ignore_claude(self):
        code = ('import sys,json; from pathlib import Path; sys.path.insert(0,sys.argv[1]); '
                'from lib.utils import get_plugin_root,get_history_home; '
                'print(json.dumps([str(get_plugin_root()),str(get_history_home())]))')
        result = subprocess.run([__import__('sys').executable, '-c', code, str(PACKAGE / 'scripts')],
                                cwd=self.project, env=self.env, capture_output=True,
                                text=True, encoding='utf-8')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout), [str(PACKAGE), str(self.home)])

    def git(self, *args):
        result = subprocess.run(['git', *args], cwd=self.repo, env=self.env,
                                capture_output=True, text=True, encoding='utf-8')
        self.assertEqual(result.returncode, 0, result.stderr)
        return result.stdout.strip()

    def test_git_fixture_only_commit_and_failure_protocols(self):
        self.repo = self.base / 'disposable-repository'
        self.repo.mkdir()
        self.git('init')
        self.git('config', 'user.email', 'fixture@example.invalid')
        self.git('config', 'user.name', 'Disposable Fixture')
        self.git('config', 'commit.gpgsign', 'false')
        self.git('config', 'core.hooksPath', '.git/hooks')
        tracked = self.repo / 'tracked.txt'
        tracked.write_text('before\n', encoding='utf-8')
        self.git('add', 'tracked.txt')
        self.git('commit', '-m', 'fixture initial')
        tracked.write_text('after\n', encoding='utf-8')
        untracked = self.repo / 'untracked.txt'
        untracked.write_text('keep untracked\n', encoding='utf-8')
        self.assertTrue(self.output('wrap_up.py', '--check', cwd=self.repo).startswith('DIRTY:'))
        self.assertIn('tracked.txt', self.output('wrap_up.py', '--diff-stat', cwd=self.repo))
        result = self.output('wrap_up.py', '--commit', 'fixture tracked change', cwd=self.repo)
        self.assertIn('UNTRACKED:', result)
        self.assertIn('COMMITTED:', result)
        self.assertEqual(self.git('ls-files', '--others', '--exclude-standard'), 'untracked.txt')
        self.assertEqual(self.git('show', 'HEAD:tracked.txt'), 'after')
        untracked.unlink()
        self.assertEqual(self.output('wrap_up.py', '--check', cwd=self.repo), 'CLEAN')
        hook = self.repo / '.git/hooks/pre-commit'
        hook.write_text('#!/bin/sh\necho deliberate-fixture-failure >&2\nexit 1\n', encoding='utf-8')
        hook.chmod(0o755)
        tracked.write_text('rejected\n', encoding='utf-8')
        head = self.git('rev-parse', 'HEAD')
        failed = self.output('wrap_up.py', '--commit', 'fixture rejected', cwd=self.repo)
        self.assertTrue(failed.startswith('FAILED:'), failed)
        self.assertIn('deliberate-fixture-failure', failed)
        self.assertEqual(self.git('rev-parse', 'HEAD'), head)
