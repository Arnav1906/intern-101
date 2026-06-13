"""Steps 1-3 of /visualise: resolve target, detect files, extract AST/structural nodes+edges → graph.json skeleton."""

import sys
import os
import json
import hashlib
import re
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / 'lib'))

SKIP_DIRS = {'.git', 'node_modules', '__pycache__', '.venv', 'venv', 'visualise-out',
             'graphify-out', 'map-out', '.claude', 'dist', 'build', 'target', '.idea'}
CODE_EXT = {'.py', '.js', '.ts', '.jsx', '.tsx', '.java', '.cs', '.cpp', '.c', '.h', '.go',
            '.rs', '.rb', '.php', '.swift', '.kt', '.scala', '.sql', '.sh', '.ps1', '.r'}
DOC_EXT = {'.md', '.txt', '.rst', '.adoc', '.yaml', '.yml', '.json', '.toml', '.ini', '.cfg', '.xml'}
IMG_EXT = {'.png', '.jpg', '.jpeg', '.gif', '.svg', '.webp'}


def _file_hash(path: Path) -> str:
    try:
        h = hashlib.sha256()
        with path.open('rb') as fh:
            while chunk := fh.read(65536):
                h.update(chunk)
        return h.hexdigest()
    except OSError:
        return ""


def detect_files(target: Path) -> dict:
    results = {'code': [], 'doc': [], 'image': [], 'other': []}
    hashes = {}
    for root, dirs, files in os.walk(target):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS and not d.startswith('.')]
        for f in files:
            fp = Path(root) / f
            rel = str(fp.relative_to(target))
            ext = fp.suffix.lower()
            h = _file_hash(fp)
            if not h:
                continue
            hashes[rel] = h
            if ext in CODE_EXT:
                results['code'].append(rel)
            elif ext in DOC_EXT:
                results['doc'].append(rel)
            elif ext in IMG_EXT:
                results['image'].append(rel)
    return results, hashes


# --- Python AST extraction (no ast module to avoid interpreter confusion, use regex) ---

def _extract_python(rel: str, content: str) -> dict:
    nodes, edges = [], []
    mod_id = rel.replace('/', '_').replace(os.sep, '_').replace('.', '_').rstrip('_')
    nodes.append({'id': mod_id, 'label': Path(rel).stem, 'type': 'module',
                  'source_file': rel, 'source_location': None})

    # imports → edges
    for m in re.finditer(r'^(?:import|from)\s+([\w.]+)', content, re.MULTILINE):
        imp = m.group(1).replace('.', '_')
        edges.append({'source': mod_id, 'target': imp, 'relation': 'imports',
                      'confidence': 'EXTRACTED', 'confidence_score': 1.0})

    # classes
    for m in re.finditer(r'^class\s+(\w+)', content, re.MULTILINE):
        cid = f"{mod_id}_{m.group(1)}"
        nodes.append({'id': cid, 'label': m.group(1), 'type': 'class',
                      'source_file': rel, 'source_location': f"L{content[:m.start()].count(chr(10))+1}"})
        edges.append({'source': mod_id, 'target': cid, 'relation': 'contains',
                      'confidence': 'EXTRACTED', 'confidence_score': 1.0})

    # top-level functions
    for m in re.finditer(r'^def\s+(\w+)', content, re.MULTILINE):
        fid = f"{mod_id}_{m.group(1)}"
        nodes.append({'id': fid, 'label': m.group(1), 'type': 'function',
                      'source_file': rel, 'source_location': f"L{content[:m.start()].count(chr(10))+1}"})
        edges.append({'source': mod_id, 'target': fid, 'relation': 'contains',
                      'confidence': 'EXTRACTED', 'confidence_score': 1.0})

    return {'source_file': rel, 'nodes': nodes, 'edges': edges}


def _extract_sql(rel: str, content: str) -> dict:
    nodes, edges = [], []
    procs = re.findall(r'CREATE\s+(?:OR\s+REPLACE\s+)?(?:PROCEDURE|FUNCTION)\s+(\w+)', content, re.IGNORECASE)
    tables = re.findall(r'CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?(\w+)', content, re.IGNORECASE)
    calls = re.findall(r'(?:EXEC|EXECUTE|CALL)\s+(\w+)', content, re.IGNORECASE)
    accessed = re.findall(r'(?:FROM|JOIN|INSERT\s+INTO|UPDATE)\s+(\w+)', content, re.IGNORECASE)

    for p in procs:
        nodes.append({'id': p, 'label': p, 'type': 'procedure', 'source_file': rel})
    for t in tables:
        nodes.append({'id': t, 'label': t, 'type': 'table', 'source_file': rel})
    for caller in procs:
        for callee in calls:
            edges.append({'source': caller, 'target': callee, 'relation': 'calls',
                          'confidence': 'INFERRED', 'confidence_score': 0.75})
        for table in accessed:
            edges.append({'source': caller, 'target': table, 'relation': 'accesses',
                          'confidence': 'INFERRED', 'confidence_score': 0.75})
    return {'source_file': rel, 'nodes': nodes, 'edges': edges}


def _extract_js_ts(rel: str, content: str) -> dict:
    nodes, edges = [], []
    file_id = rel.replace('/', '_').replace(os.sep, '_').replace('.', '_').rstrip('_')
    nodes.append({'id': file_id, 'label': Path(rel).stem, 'type': 'module', 'source_file': rel})

    for m in re.finditer(r'(?:import\s.+?from\s+["\'](.+?)["\']|require\s*\(\s*["\'](.+?)["\']\s*\))', content):
        mod = m.group(1) or m.group(2)
        edges.append({'source': file_id, 'target': mod.replace('/', '_').replace('.', '_'),
                      'relation': 'imports', 'confidence': 'EXTRACTED', 'confidence_score': 1.0})

    for m in re.finditer(r'(?:^|\s)(?:function|class)\s+(\w+)', content, re.MULTILINE):
        nid = f"{file_id}_{m.group(1)}"
        nodes.append({'id': nid, 'label': m.group(1), 'type': 'function', 'source_file': rel})
        edges.append({'source': file_id, 'target': nid, 'relation': 'contains',
                      'confidence': 'EXTRACTED', 'confidence_score': 1.0})

    return {'source_file': rel, 'nodes': nodes, 'edges': edges}


def extract_code_file(rel: str, target: Path) -> dict:
    fp = target / rel
    try:
        content = fp.read_text(encoding='utf-8', errors='replace')
    except OSError:
        return {'source_file': rel, 'nodes': [], 'edges': []}
    ext = fp.suffix.lower()
    if ext == '.py':
        return _extract_python(rel, content)
    elif ext == '.sql':
        return _extract_sql(rel, content)
    elif ext in {'.js', '.ts', '.jsx', '.tsx'}:
        return _extract_js_ts(rel, content)
    else:
        # minimal: just register file as a node
        file_id = rel.replace('/', '_').replace(os.sep, '_').replace('.', '_').rstrip('_')
        return {'source_file': rel,
                'nodes': [{'id': file_id, 'label': Path(rel).stem, 'type': 'file', 'source_file': rel}],
                'edges': []}


def merge_extractions(cache_dir: Path, current_files: set) -> dict:
    all_nodes, all_edges = [], []
    seen_ids: set = set()
    for f in cache_dir.glob('ast_*.json'):
        try:
            d = json.loads(f.read_text(encoding='utf-8'))
            if d.get('source_file', '') not in current_files:
                f.unlink()
                continue
            for n in d.get('nodes', []):
                if n['id'] not in seen_ids:
                    seen_ids.add(n['id'])
                    all_nodes.append(n)
            all_edges.extend(d.get('edges', []))
        except Exception as e:
            print(f"Warning: could not read {f}: {e}", file=sys.stderr)
    return {'nodes': all_nodes, 'edges': all_edges}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("target", nargs="?", default="", help="target directory (default: cwd)")
    parser.add_argument("--update", action="store_true")
    parser.add_argument("--no-viz", action="store_true")
    parser.add_argument("--cluster-only", action="store_true")
    args = parser.parse_args()

    cwd = Path.cwd()
    raw_target = args.target.strip()

    target = (cwd / raw_target).resolve() if raw_target else cwd.resolve()

    # boundary check
    safe_root = cwd.resolve()
    if target != safe_root and not str(target).startswith(str(safe_root) + os.sep):
        print(f"BOUNDARY_ERROR:{target}")
        sys.exit(1)

    if not target.is_dir():
        print(f"NOTFOUND:{target}")
        sys.exit(1)

    out_dir = target / 'visualise-out'
    cache_dir = out_dir / 'cache'
    cache_dir.mkdir(parents=True, exist_ok=True)

    print(f"TARGET:{target}")

    # detect files
    results, hashes = detect_files(target)
    detect_data = {'files': results, 'hashes': hashes, 'target': str(target)}
    (out_dir / '.detect.json').write_text(json.dumps(detect_data, indent=2), encoding='utf-8')

    total = sum(len(v) for v in results.values())
    print(f"Detected {total} files: {len(results['code'])} code, {len(results['doc'])} docs, {len(results['image'])} images")

    if total == 0:
        sys.exit(0)

    # load old hashes for --update mode
    old_hashes: dict = {}
    if args.update:
        old_detect_path = out_dir / '.detect.json'
        if old_detect_path.exists():
            try:
                old_data = json.loads(old_detect_path.read_text(encoding='utf-8'))
                old_hashes = old_data.get('hashes', {})
            except Exception:
                pass

    # extract code files
    for rel in results['code']:
        if args.update and old_hashes.get(rel) == hashes.get(rel):
            continue  # unchanged
        file_hash = hashes.get(rel, rel)[:8]
        cache_path = cache_dir / f"ast_{file_hash}.json"
        extracted = extract_code_file(rel, target)
        cache_path.write_text(json.dumps(extracted, indent=2), encoding='utf-8')

    current_files = set(results['code'])
    merged = merge_extractions(cache_dir, current_files)
    (out_dir / '.ast_merged.json').write_text(json.dumps(merged, indent=2), encoding='utf-8')
    print(f"AST extraction: {len(merged['nodes'])} nodes, {len(merged['edges'])} edges from code files")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"ERROR:{e}", file=sys.stderr)
        sys.exit(1)
