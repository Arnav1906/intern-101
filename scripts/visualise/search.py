"""visualise-search helpers: load graph, parse args, prepare node search text, show neighbors."""

import sys
import os
import json
import re
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from lib.graph import load_graph, get_neighbors, get_node


def load_graph_or_exit(cwd: Path) -> dict:
    out_dir = cwd / 'visualise-out'
    graph_path = out_dir / 'graph.json'
    if not graph_path.exists():
        print("NOTFOUND")
        sys.exit(0)
    graph = load_graph(out_dir)
    nodes = graph.get('nodes', [])
    edges = graph.get('edges', [])
    print(f"LOADED:{len(nodes)} nodes,{len(edges)} edges")
    return graph


def prepare_nodes(graph: dict, community_filter: int | None) -> list:
    nodes = graph.get('nodes', [])
    if community_filter is not None:
        nodes = [n for n in nodes if n.get('community') == community_filter]
    prepared = []
    for n in nodes:
        parts = [
            n.get('label', n.get('id', '')),
            n.get('type', ''),
            n.get('source_file', '').replace('/', ' ').replace(os.sep, ' ').replace('_', ' '),
            n.get('rationale', ''),
        ]
        search_text = ' '.join(p for p in parts if p).lower()
        prepared.append({
            'id': n['id'],
            'label': n.get('label', n['id']),
            'type': n.get('type', ''),
            'community': n.get('community'),
            'degree': n.get('degree', 0),
            'source_file': n.get('source_file', ''),
            'rationale': n.get('rationale', ''),
            'search_text': search_text,
        })
    return prepared


def show_neighbors(graph: dict, node_id: str) -> None:
    node_data = get_node(graph, node_id) or {}
    neighbors_in = []
    neighbors_out = []
    for e in graph.get('edges', []):
        src, tgt = e.get('source'), e.get('target')
        rel = e.get('relation', '')
        conf = e.get('confidence', '')
        if src == node_id:
            neighbors_out.append({'node': tgt, 'relation': rel, 'confidence': conf})
        elif tgt == node_id:
            neighbors_in.append({'node': src, 'relation': rel, 'confidence': conf})

    node_index = {n['id']: n.get('label', n['id']) for n in graph.get('nodes', [])}

    print(f"Node: {node_data.get('label', node_id)}")
    print(f"Community: {node_data.get('community')} · Degree: {node_data.get('degree', 0)}")
    print(f"Source: {node_data.get('source_file', '?')}")
    all_nb = [('outbound', nb) for nb in neighbors_out] + [('inbound', nb) for nb in neighbors_in]
    print(f"Neighbors ({len(all_nb)}):")
    for direction, nb in all_nb:
        label = node_index.get(nb['node'], nb['node'])
        print(f"  {direction:8} [{nb['confidence']:9}] {nb['relation']:20} → {label}")


def main():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd")

    load_p = sub.add_parser("load")

    prep_p = sub.add_parser("prepare")
    prep_p.add_argument("--community", type=int, default=None)

    nb_p = sub.add_parser("neighbors")
    nb_p.add_argument("node_id")

    args = parser.parse_args()
    cwd = Path.cwd()

    if args.cmd == "load":
        load_graph_or_exit(cwd)

    elif args.cmd == "prepare":
        out_dir = cwd / 'visualise-out'
        graph = load_graph(out_dir)
        prepared = prepare_nodes(graph, args.community)
        print(json.dumps(prepared))

    elif args.cmd == "neighbors":
        out_dir = cwd / 'visualise-out'
        graph = load_graph(out_dir)
        show_neighbors(graph, args.node_id)

    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"ERROR:{e}", file=sys.stderr)
        sys.exit(1)
