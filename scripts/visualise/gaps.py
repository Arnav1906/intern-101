"""Find isolated nodes in graph.json and optionally scaffold stub docs."""
import sys
import json
import re
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / 'lib'))
from utils import get_plugin_root, ensure_dir
from graph import load_graph, get_isolated_nodes, graph_stats


def main():
    args = ' '.join(sys.argv[1:])
    draft = '--draft' in args
    filter_ext = None
    fm = re.search(r'--filter\s+(\S+)', args)
    if fm:
        filter_ext = '.' + fm.group(1).lstrip('.')

    cwd = Path.cwd()
    visualise_out = cwd / 'visualise-out'
    graph = load_graph(visualise_out)

    if not graph['nodes']:
        print('NOTFOUND')
        return

    gaps = get_isolated_nodes(graph)

    if filter_ext:
        gaps = [g for g in gaps if g.get('source_file', '').endswith(filter_ext)]

    stats = graph_stats(graph)
    print(f'GAPS:{len(gaps)}')
    print(f'DRAFT:{draft}')
    print(f'TOTAL_NODES:{stats["node_count"]}')
    print(json.dumps(gaps))

    if draft:
        stubs_dir = visualise_out / 'gap-stubs'
        ensure_dir(stubs_dir)
        print('STUBS_DIR_READY')


if __name__ == '__main__':
    main()
