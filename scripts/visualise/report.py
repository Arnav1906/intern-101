"""Generate GRAPH_REPORT.md from visualise-out/graph.json."""

import sys
import argparse
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from lib.graph import load_graph


def _top_connections(node_id, edges, n=3):
    out = []
    for edge in edges:
        src = edge.get('source', '')
        tgt = edge.get('target', '')
        label = edge.get('label', '')
        if src == node_id:
            out.append((tgt, label))
        elif tgt == node_id:
            out.append((src, label))
    return out[:n]


def _cross_cluster_edges(cluster_ids, edges, n=5):
    out = []
    for edge in edges:
        src = edge.get('source', '')
        tgt = edge.get('target', '')
        if src in cluster_ids and tgt not in cluster_ids:
            out.append((src, tgt, edge.get('label', '')))
    return out[:n]


def generate_report(graph, out_path):
    nodes = graph.get('nodes', [])
    edges = graph.get('edges', [])

    lines = ['# Knowledge Graph Report', '']

    # Section 1: Architecture by Cluster
    lines.append('## Architecture by Cluster')
    lines.append('')

    clusters = defaultdict(list)
    for node in nodes:
        key = node.get('community')
        bucket = str(key) if key is not None else 'unclustered'
        clusters[bucket].append(node)

    for community, cluster_nodes in sorted(clusters.items(), key=lambda x: -len(x[1])):
        lines.append('### Cluster {} ({} nodes)'.format(community, len(cluster_nodes)))
        lines.append('')
        cluster_ids = {n.get('id', '') for n in cluster_nodes}

        for node in sorted(cluster_nodes, key=lambda n: n.get('id', '')):
            nid = node.get('id', '')
            ntype = node.get('type', '')
            desc = node.get('description', '')
            if desc:
                lines.append('- **{}** ({}) — {}'.format(nid, ntype, desc))
            else:
                lines.append('- **{}** ({})'.format(nid, ntype))

        cross = _cross_cluster_edges(cluster_ids, edges, n=5)
        if cross:
            lines.append('')
            lines.append('Cross-cluster connections:')
            for src, tgt, label in cross:
                if label:
                    lines.append('- {} → {} [{}]'.format(src, tgt, label))
                else:
                    lines.append('- {} → {}'.format(src, tgt))
        lines.append('')

    # Section 2: Node Reference
    lines.append('## Node Reference')
    lines.append('')

    for node in sorted(nodes, key=lambda n: n.get('id', '')):
        nid = node.get('id', '')
        ntype = node.get('type', '')
        confidence = node.get('confidence', '')
        desc = node.get('description', '')

        lines.append('### {}'.format(nid))
        type_line = 'Type: {}'.format(ntype)
        if confidence:
            type_line += ' | Confidence: {}'.format(confidence)
        lines.append(type_line)
        if desc:
            lines.append(desc)

        conns = _top_connections(nid, edges, n=3)
        if conns:
            parts = ['{} ({})'.format(tgt, lbl) if lbl else tgt for tgt, lbl in conns]
            lines.append('Connections: {}'.format(', '.join(parts)))
        lines.append('')

    out_path.write_text('\n'.join(lines), encoding='utf-8')
    print('WRITTEN:{}'.format(out_path))


def main():
    parser = argparse.ArgumentParser(description='Generate GRAPH_REPORT.md from graph.json')
    parser.add_argument('--path', default='', help='Path to graph.json (default: visualise-out/graph.json)')
    args = parser.parse_args()

    cwd = Path.cwd()
    graph_path = Path(args.path).resolve() if args.path else cwd / 'visualise-out' / 'graph.json'

    if not graph_path.exists():
        print('ERROR:graph.json not found at {}'.format(graph_path), file=sys.stderr)
        sys.exit(1)

    graph = load_graph(graph_path.parent)

    if not graph.get('nodes'):
        print('ERROR:graph.json has no nodes', file=sys.stderr)
        sys.exit(1)

    out_path = graph_path.parent / 'GRAPH_REPORT.md'
    generate_report(graph, out_path)


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print('ERROR:{}'.format(e), file=sys.stderr)
        sys.exit(1)
