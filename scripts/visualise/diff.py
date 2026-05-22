"""visualise-diff helpers: parse refs, compute node/edge diff, write .diff_data.json."""

import sys
import json
import subprocess
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / 'lib'))


def _resolve_ref(ref: str, cwd: Path, snaps_dir: Path, safe_root: Path) -> str:
    if ref.endswith('.json'):
        candidate = Path(ref) if Path(ref).is_absolute() else cwd / ref
        real = candidate.resolve()
        if not (real == safe_root or str(real).startswith(str(safe_root))):
            return f"BOUNDARY_ERROR:{candidate}"
        if candidate.exists():
            return str(candidate)
        return f"ERROR:{ref}"

    result = subprocess.run(
        ['git', 'rev-parse', '--short=12', ref],
        capture_output=True, text=True, cwd=str(cwd)
    )
    if result.returncode != 0:
        return f"ERROR:{ref}"
    sha = result.stdout.strip()
    snap_file = snaps_dir / f"{sha}.json"
    if snap_file.exists():
        return str(snap_file)
    return f"NEED_SNAPSHOT:{sha}"


def compute_diff(path_a: str, path_b: str, out_dir: Path) -> dict:
    snap_a = json.loads(Path(path_a).read_text(encoding='utf-8'))
    snap_b = json.loads(Path(path_b).read_text(encoding='utf-8'))

    nodes_a = {n['id']: n for n in snap_a.get('nodes', [])}
    nodes_b = {n['id']: n for n in snap_b.get('nodes', [])}
    edges_a = {(e['source'], e['target']): e for e in snap_a.get('edges', [])}
    edges_b = {(e['source'], e['target']): e for e in snap_b.get('edges', [])}

    added_nodes = {nid: n for nid, n in nodes_b.items() if nid not in nodes_a}
    removed_nodes = {nid: n for nid, n in nodes_a.items() if nid not in nodes_b}
    shared = {nid: (nodes_a[nid], nodes_b[nid]) for nid in nodes_a if nid in nodes_b}
    shifted = {
        nid: (na, nb) for nid, (na, nb) in shared.items()
        if na.get('community') != nb.get('community')
        and na.get('community') is not None and nb.get('community') is not None
    }

    added_edges = {k: e for k, e in edges_b.items() if k not in edges_a}
    removed_edges = {k: e for k, e in edges_a.items() if k not in edges_b}

    diff = {
        'meta_a': {'sha': snap_a.get('sha_short', '?'), 'date': snap_a.get('date', '?')[:10],
                   'message': snap_a.get('message', '?')},
        'meta_b': {'sha': snap_b.get('sha_short', '?'), 'date': snap_b.get('date', '?')[:10],
                   'message': snap_b.get('message', '?')},
        'added_nodes': list(added_nodes.values()),
        'removed_nodes': list(removed_nodes.values()),
        'shifted_nodes': [
            {'id': nid, 'from_community': na.get('community'), 'to_community': nb.get('community'),
             'label': nb.get('label', nid)}
            for nid, (na, nb) in shifted.items()
        ],
        'added_edges': list(added_edges.values()),
        'removed_edges': list(removed_edges.values()),
        'stats': {
            'nodes_added': len(added_nodes), 'nodes_removed': len(removed_nodes),
            'nodes_shifted': len(shifted),
            'edges_added': len(added_edges), 'edges_removed': len(removed_edges),
            'nodes_a': len(nodes_a), 'nodes_b': len(nodes_b),
            'edges_a': len(edges_a), 'edges_b': len(edges_b),
        }
    }

    out_path = out_dir / '.diff_data.json'
    out_path.write_text(json.dumps(diff, indent=2), encoding='utf-8')
    return diff


def main():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd")

    resolve_p = sub.add_parser("resolve")
    resolve_p.add_argument("ref_a")
    resolve_p.add_argument("ref_b")

    diff_p = sub.add_parser("diff")
    diff_p.add_argument("path_a")
    diff_p.add_argument("path_b")

    args = parser.parse_args()
    cwd = Path.cwd()
    out_dir = cwd / 'visualise-out'
    snaps_dir = out_dir / 'snapshots'
    safe_root = cwd.resolve()

    if args.cmd == "resolve":
        a = _resolve_ref(args.ref_a, cwd, snaps_dir, safe_root)
        b = _resolve_ref(args.ref_b, cwd, snaps_dir, safe_root)
        print(f"A:{a}")
        print(f"B:{b}")

    elif args.cmd == "diff":
        diff = compute_diff(args.path_a, args.path_b, out_dir)
        s = diff['stats']
        print(f"Diff: +{s['nodes_added']} nodes, -{s['nodes_removed']} nodes, ~{s['nodes_shifted']} shifted")
        print(f"      +{s['edges_added']} edges, -{s['edges_removed']} edges")
        print(f"      {s['nodes_a']} nodes → {s['nodes_b']} nodes  |  {s['edges_a']} edges → {s['edges_b']} edges")

    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"ERROR:{e}", file=sys.stderr)
        sys.exit(1)
