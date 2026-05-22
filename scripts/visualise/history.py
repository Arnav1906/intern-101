"""visualise-history helpers: check prerequisites, list commits, snapshot graph at each commit, prepare history HTML data."""

import sys
import json
import re
import subprocess
import argparse
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent / 'lib'))

CODE_EXT = {'.py', '.js', '.ts', '.jsx', '.tsx', '.java', '.sql', '.cs', '.go', '.rs', '.rb'}
SKIP_DIRS = {'.git', 'node_modules', '__pycache__', '.venv', 'visualise-out', 'graphify-out'}


def _git(cwd: Path, *args, timeout: int = 30) -> tuple[int, str]:
    try:
        r = subprocess.run(['git', *args], capture_output=True, text=True, cwd=str(cwd), timeout=timeout)
        return r.returncode, r.stdout.strip()
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return -1, ""


def check_prereqs(cwd: Path) -> None:
    out_dir = cwd / 'visualise-out'
    snaps_dir = out_dir / 'snapshots'
    snaps_dir.mkdir(parents=True, exist_ok=True)

    code, _ = _git(cwd, 'rev-parse', '--is-inside-work-tree')
    is_git = code == 0
    has_graph = (out_dir / 'graph.json').exists()

    print(f"GIT:{is_git}")
    print(f"HAS_GRAPH:{has_graph}")
    print(f"CWD:{cwd}")


def get_commits(cwd: Path, args_str: str) -> None:
    commits_m = re.search(r'--commits\s+(\d+)', args_str)
    since_m = re.search(r'--since\s+(\S+)', args_str)

    if commits_m:
        limit = int(commits_m.group(1))
        cmd = ['git', 'log', f'--max-count={limit}', '--format=%H|%ai|%s']
    elif since_m:
        since = since_m.group(1)
        if re.match(r'\d+[dwmyDWMY]$', since):
            n = int(since[:-1])
            unit_map = {'d': 'days', 'w': 'weeks', 'm': 'months', 'y': 'years',
                        'D': 'days', 'W': 'weeks', 'M': 'months', 'Y': 'years'}
            since_git = f"{n} {unit_map[since[-1]]} ago"
        else:
            since_git = since
        cmd = ['git', 'log', f'--since={since_git}', '--format=%H|%ai|%s']
    else:
        cmd = ['git', 'log', '--max-count=10', '--format=%H|%ai|%s']

    code, out = _git(cwd, *cmd[1:])
    lines = [l.strip() for l in out.split('\n') if l.strip()]
    print(f"COMMITS:{len(lines)}")
    for l in lines:
        print(l)


def _get_changed_files(cwd: Path, sha: str) -> list:
    _, out = _git(cwd, 'diff-tree', '--no-commit-id', '-r', '--name-only', sha)
    return [f.strip() for f in out.split('\n') if f.strip()]


def _extract_quick(cwd: Path, sha: str, files: list) -> tuple[dict, list]:
    nodes: dict = {}
    edges = []
    for fpath in files:
        ext = Path(fpath).suffix.lower()
        if ext not in CODE_EXT:
            continue
        code, content = _git(cwd, 'show', f'{sha}:{fpath}', timeout=10)
        if code != 0:
            continue
        node_id = fpath.replace('/', '_').replace('.', '_')
        nodes[node_id] = {'id': node_id, 'label': Path(fpath).name, 'source_file': fpath}

        if ext == '.py':
            for m in re.finditer(r'^(?:import|from)\s+([\w.]+)', content, re.MULTILINE):
                imp_id = m.group(1).replace('.', '_')
                nodes.setdefault(imp_id, {'id': imp_id, 'label': m.group(1)})
                edges.append({'source': node_id, 'target': imp_id, 'relation': 'imports'})
        elif ext == '.sql':
            procs = re.findall(r'CREATE\s+(?:OR\s+REPLACE\s+)?(?:PROCEDURE|FUNCTION)\s+(\w+)', content, re.IGNORECASE)
            calls = re.findall(r'(?:EXEC|EXECUTE|CALL)\s+(\w+)', content, re.IGNORECASE)
            for p in procs:
                nodes[p] = {'id': p, 'label': p, 'type': 'procedure'}
            for p in procs:
                for c in calls:
                    edges.append({'source': p, 'target': c, 'relation': 'calls'})
    return nodes, edges


def snapshot_commits(cwd: Path, commits_raw: list) -> None:
    out_dir = cwd / 'visualise-out'
    snaps_dir = out_dir / 'snapshots'
    snaps_dir.mkdir(parents=True, exist_ok=True)

    for line in commits_raw:
        parts = line.split('|', 2)
        if len(parts) < 3:
            continue
        sha, date, message = parts[0].strip(), parts[1].strip(), parts[2].strip()
        short = sha[:12]
        snap_file = snaps_dir / f"{short}.json"
        if snap_file.exists():
            print(f"Cached: {sha[:8]} {message[:40]}")
            continue
        changed = _get_changed_files(cwd, sha)
        nodes, edges = _extract_quick(cwd, sha, changed)
        snap = {
            'sha': sha, 'sha_short': sha[:8], 'date': date, 'message': message,
            'n_nodes': len(nodes), 'n_edges': len(edges),
            'nodes': list(nodes.values()), 'edges': edges,
            'changed_files': changed,
        }
        snap_file.write_text(json.dumps(snap), encoding='utf-8')
        print(f"Snapped: {sha[:8]} {message[:40]} ({len(nodes)} nodes, {len(edges)} edges)")


def prepare_history_data(cwd: Path) -> None:
    snaps_dir = cwd / 'visualise-out' / 'snapshots'
    snaps = []
    for f in sorted(snaps_dir.glob('*.json'), reverse=True):
        try:
            snaps.append(json.loads(f.read_text(encoding='utf-8')))
        except Exception:
            pass
    # escape </script> sequences so commit messages cannot break out of a script tag
    out_data = json.dumps(snaps, ensure_ascii=False).replace('</', '<\\/')
    tmpl_path = cwd / 'visualise-out' / '_history_tmpl.txt'
    tmpl_path.write_text(out_data, encoding='utf-8')
    print(f"SNAP_COUNT:{len(snaps)}")
    print(f"TMPL_PATH:{tmpl_path}")
    print("DATA_WRITTEN")


def main():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd")

    sub.add_parser("check")

    commits_p = sub.add_parser("commits")
    commits_p.add_argument("args_str", nargs="?", default="")

    snap_p = sub.add_parser("snapshot")
    snap_p.add_argument("commits_json")

    sub.add_parser("prepare-data")

    args = parser.parse_args()
    cwd = Path.cwd()

    if args.cmd == "check":
        check_prereqs(cwd)
    elif args.cmd == "commits":
        get_commits(cwd, args.args_str)
    elif args.cmd == "snapshot":
        commits_raw = json.loads(args.commits_json)
        snapshot_commits(cwd, commits_raw)
    elif args.cmd == "prepare-data":
        prepare_history_data(cwd)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"ERROR:{e}", file=sys.stderr)
        sys.exit(1)
