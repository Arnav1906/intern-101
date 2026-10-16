"""Standalone archive, sparse checkout, and copied installed-resource proofs."""
from datetime import datetime
import json
import os
from pathlib import Path
import re
import runpy
import shutil
import subprocess
import sys
import tempfile
import unittest
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[2]
IGNORE = shutil.ignore_patterns('__pycache__', '*.pyc', '*.pyo')


def git(*args, cwd):
    return subprocess.run(['git', *args], cwd=cwd, check=True,
                          capture_output=True, text=True, encoding='utf-8')


def copy_snapshot(snapshot):
    """Commit exclusively in a disposable fixture, never in the source tree."""
    snapshot.mkdir()
    for relative in ('.claude-plugin', '.agents/plugins',
                     'plugins/intern-101-claude', 'plugins/intern-101-codex'):
        shutil.copytree(ROOT / relative, snapshot / relative, ignore=IGNORE)
    git('init', cwd=snapshot)
    git('config', 'user.name', 'Disposable Package Fixture', cwd=snapshot)
    git('config', 'user.email', 'fixture@example.invalid', cwd=snapshot)
    git('config', 'commit.gpgsign', 'false', cwd=snapshot)
    git('config', 'core.hooksPath', '.git/hooks', cwd=snapshot)
    git('add', '.', cwd=snapshot)
    git('commit', '-m', 'disposable package fixture', cwd=snapshot)


def sparse_copy(base, snapshot, agent):
    catalog = '.claude-plugin' if agent == 'claude' else '.agents/plugins'
    plugin = 'plugins/intern-101-' + agent
    checkout = base / (agent + '-checkout')
    git('clone', '--no-checkout', '--no-local', str(snapshot), str(checkout), cwd=base)
    git('sparse-checkout', 'init', '--cone', cwd=checkout)
    git('sparse-checkout', 'set', catalog, plugin, cwd=checkout)
    git('checkout', cwd=checkout)
    installed = base / ('cache with spaces-\u00e9') / agent / 'intern-101'
    shutil.copytree(checkout / plugin, installed, ignore=IGNORE)
    return checkout, installed


class PackageIsolation(unittest.TestCase):
    def test_codex_archive_is_complete_and_exclusive(self):
        build = runpy.run_path(str(ROOT / 'tools/build_codex.py'))['build']
        with tempfile.TemporaryDirectory() as folder:
            archive = build(ROOT, Path(folder))
            with ZipFile(archive) as zipped:
                names = set(zipped.namelist())
            self.assertIn('intern-101-codex/agents/chat-context-extractor.md', names)
            self.assertIn('intern-101-codex/scripts/latest_session.py', names)
            self.assertIn('intern-101-codex/scripts/chat_context_extractor.py', names)
            expected = {p.relative_to(ROOT / 'plugins').as_posix()
                        for p in (ROOT / 'plugins/intern-101-codex').rglob('*')
                        if p.is_file() and (p.suffix in ('.md', '.py') or
                           p.name == 'LICENSE' or p.name == 'plugin.json')
                        and 'tests' not in p.relative_to(ROOT / 'plugins/intern-101-codex').parts
                        and '__pycache__' not in p.parts}
            self.assertEqual(names, expected)
            self.assertFalse(any('intern-101-claude' in name for name in names))
            self.assertFalse(any('__pycache__' in name or '/tests/' in name for name in names))

    def assert_resources(self, installed, agent):
        manifest = json.loads((installed / ('.claude-plugin' if agent == 'claude'
                              else '.codex-plugin') / 'plugin.json').read_text(encoding='utf-8'))
        for key in ('skills', 'agents', 'rules', 'scripts'):
            paths = manifest.get(key, [])
            for relative in ([paths] if isinstance(paths, str) else paths):
                target = (installed / relative).resolve()
                self.assertTrue(target.is_relative_to(installed.resolve()))
                self.assertTrue(target.exists(), target)
        skills = list((installed / 'skills').glob('*/SKILL.md'))
        self.assertEqual(len(skills), 9)
        documents = skills + list((installed / 'references').glob('*.md'))
        for document in documents:
            text = document.read_text(encoding='utf-8')
            for relative in re.findall(r'(?:\$\{CLAUDE_PLUGIN_ROOT\}|<plugin-root>)/([\w./-]+)', text):
                self.assertTrue((installed / relative).exists(), (document, relative))
            for relative in re.findall(r'\]\(([^)]+)\)', text):
                # The organization prompt includes a generated project-index template.
                if relative != '_Index.md' and not relative.startswith(('http:', 'https:', '#')):
                    target = (document.parent / relative.split('#')[0]).resolve()
                    self.assertTrue(target.is_relative_to(installed.resolve()), (document, relative))
                    self.assertTrue(target.exists(), (document, relative))
            for relative in re.findall(r'`((?:agents|scripts|rules|references)/[\w./-]+\.(?:md|py))`', text):
                self.assertTrue((installed / relative).is_file(), (document, relative))
        if agent == 'claude':
            hooks = json.loads((installed / 'hooks/hooks.json').read_text(encoding='utf-8'))
            for relative in re.findall(r'\$\{CLAUDE_PLUGIN_ROOT\}/([\w./-]+)', json.dumps(hooks)):
                self.assertTrue((installed / relative).is_file(), relative)

    def exercise_installed(self, base, installed, agent):
        project = base / 'unrelated project-\u00e9'
        project.mkdir()
        home = base / 'fixture home'
        home.mkdir()
        codex_home = home / '.codex'
        env = dict(os.environ, HOME=str(home), USERPROFILE=str(home),
                   CODEX_HOME=str(codex_home), CLAUDE_PLUGIN_ROOT=str(installed),
                   PYTHONDONTWRITEBYTECODE='1', PYTHONUTF8='1', PYTHONIOENCODING='utf-8')

        def run(script, *args):
            result = subprocess.run([sys.executable, str(installed / 'scripts' / script), *args],
                                    cwd=project, env=env, capture_output=True, text=True, encoding='utf-8')
            self.assertEqual(result.returncode, 0, result.stderr)
            return result.stdout.strip()

        for script in ('catchup.py', 'daily_update.py', 'recall.py', 'status.py'):
            self.assertEqual(run(script), 'NONE', script)
        self.assertEqual(run('wrap_up.py', '--check'), 'NO_REPO')
        sid = '11111111-1111-4111-8111-111111111111'
        timestamp = datetime.now().astimezone().isoformat()
        if agent == 'codex':
            history = codex_home / 'sessions' / 'rollout.jsonl'
            rows = [{'type': 'session_meta', 'timestamp': timestamp,
                     'payload': {'id': sid, 'cwd': str(project), 'timestamp': timestamp}}]
            for role, text in [('user', 'Save this isolated fixture conversation'),
                               ('assistant', 'The copied package resolved its own runtime')]:
                rows.append({'type': 'response_item', 'timestamp': timestamp,
                             'payload': {'type': 'message', 'role': role,
                                         'content': [{'type': 'text', 'text': text}]}})
        else:
            slug = (str(project.resolve()).replace('\\', '/').replace(':', '-').replace('/', '-')
                    .replace("'", '').replace(' ', '-').replace('_', '-').lstrip('-'))
            history = home / '.claude/projects' / slug / (sid + '.jsonl')
            rows = [{'type': role, 'sessionId': sid, 'timestamp': timestamp,
                     'message': {'content': text}} for role, text in
                    [('user', 'Save this isolated fixture conversation'),
                     ('assistant', 'The copied package resolved its own runtime')]]
        history.parent.mkdir(parents=True)
        history.write_text(''.join(json.dumps(row) + '\n' for row in rows), encoding='utf-8')
        before = history.read_bytes()
        cleaned = json.loads(run('chat_context_extractor.py', str(history)))
        self.assertEqual(cleaned['session_id'], sid)
        self.assertEqual([turn['role'] for turn in cleaned['turns']], ['user', 'assistant'])
        listed = json.loads(run('extract_today.py'))
        self.assertEqual([item['uuid'] for item in listed], [sid])
        self.assertEqual(Path(listed[0]['path']), history)
        if agent == 'codex':
            self.assertEqual(Path(run('latest_session.py')), history)
        code = ('import sys,json; sys.path.insert(0,sys.argv[1]); '
                'import lib.utils,lib.session; '
                'print(json.dumps([lib.utils.__file__,lib.session.__file__,str(lib.utils.get_plugin_root())]))')
        result = subprocess.run([sys.executable, '-c', code, str(installed / 'scripts')],
                                cwd=project, env=env, capture_output=True, text=True, encoding='utf-8')
        self.assertEqual(result.returncode, 0, result.stderr)
        for resolved in json.loads(result.stdout):
            self.assertTrue(Path(resolved).resolve().is_relative_to(installed.resolve()), resolved)
        self.assertEqual(history.read_bytes(), before)
        self.assertFalse(list(installed.rglob('__pycache__')))

    def assert_sparse_install(self, agent):
        with tempfile.TemporaryDirectory(prefix='intern101-sparse-') as folder:
            base = Path(folder)
            snapshot = base / 'snapshot'
            copy_snapshot(snapshot)
            checkout, installed = sparse_copy(base, snapshot, agent)
            sibling = 'codex' if agent == 'claude' else 'claude'
            self.assertFalse((checkout / ('plugins/intern-101-' + sibling)).exists())
            for former in ('skills', 'agents', 'scripts', 'rules', 'hooks'):
                self.assertFalse((checkout / former).exists())
            catalog_path = '.claude-plugin/marketplace.json' if agent == 'claude' else '.agents/plugins/marketplace.json'
            catalog = json.loads((checkout / catalog_path).read_text(encoding='utf-8'))
            source = catalog['plugins'][0]['source']
            relative = source if isinstance(source, str) else source['path']
            selected = checkout / relative
            self.assertTrue(selected.is_dir())
            expected = {p.relative_to(ROOT / ('plugins/intern-101-' + agent)).as_posix()
                        for p in (ROOT / ('plugins/intern-101-' + agent)).rglob('*')
                        if p.is_file() and '__pycache__' not in p.parts and p.suffix not in ('.pyc', '.pyo')}
            self.assertEqual({p.relative_to(selected).as_posix() for p in selected.rglob('*') if p.is_file()}, expected)
            self.assert_resources(installed, agent)
            self.exercise_installed(base, installed, agent)

    def test_claude_sparse_installed_package(self):
        self.assert_sparse_install('claude')

    def test_codex_sparse_installed_package(self):
        self.assert_sparse_install('codex')
