"""Step 5 of /visualise: merge AST + semantic extractions, run Louvain community detection, write graph.json."""

import sys
import json
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / 'lib'))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("target", nargs="?", default="", help="target directory (default: cwd)")
    args = parser.parse_args()

    cwd = Path.cwd()
    raw_target = args.target.strip()
    target = (cwd / raw_target).resolve() if raw_target else cwd.resolve()
    out_dir = target / 'visualise-out'

    # load merged AST data
    ast_path = out_dir / '.ast_merged.json'
    if not ast_path.exists():
        print(f"ERROR:missing {ast_path} — run extract.py first", file=sys.stderr)
        sys.exit(1)

    ast_data = json.loads(ast_path.read_text(encoding='utf-8'))
    sem_path = out_dir / 'cache' / 'semantic_docs.json'
    sem_data = json.loads(sem_path.read_text(encoding='utf-8')) if sem_path.exists() else {'nodes': [], 'edges': [], 'hyperedges': []}

    try:
        import networkx as nx
    except ImportError:
        print(
            "ERROR: networkx not installed.\n"
            "Run: pip install networkx==3.3 python-louvain==0.16",
            file=sys.stderr,
        )
        sys.exit(1)

    # merge nodes (deduplicate by id)
    all_nodes: dict = {}
    for n in ast_data['nodes'] + sem_data['nodes']:
        if n['id'] not in all_nodes:
            all_nodes[n['id']] = n

    all_edges = ast_data['edges'] + sem_data['edges']
    hyperedges = sem_data.get('hyperedges', [])

    G = nx.Graph()
    for nid, ndata in all_nodes.items():
        G.add_node(nid, **ndata)
    for e in all_edges:
        src, tgt = e.get('source'), e.get('target')
        if src in all_nodes and tgt in all_nodes:
            G.add_edge(src, tgt,
                       relation=e.get('relation', 'related'),
                       confidence=e.get('confidence', 'INFERRED'),
                       confidence_score=e.get('confidence_score', 0.75))

    # community detection
    try:
        import community as community_louvain
        partition = community_louvain.best_partition(G)
        for node, comm in partition.items():
            G.nodes[node]['community'] = comm
        n_communities = len(set(partition.values()))
    except Exception as e:
        print(f"Community detection failed: {e} — assigning all to community 0", file=sys.stderr)
        for node in G.nodes():
            G.nodes[node]['community'] = 0
        n_communities = 1

    for node in G.nodes():
        G.nodes[node]['degree'] = G.degree(node)

    sorted_nodes = sorted(G.nodes(data=True), key=lambda x: x[1].get('degree', 0), reverse=True)
    god_nodes = [n for n, _ in sorted_nodes[:5]]
    gaps = [n for n in G.nodes() if G.degree(n) == 0]

    graph_data = {
        'nodes': [{'id': n, **G.nodes[n]} for n in G.nodes()],
        'edges': [{'source': u, 'target': v, **d} for u, v, d in G.edges(data=True)],
        'hyperedges': hyperedges,
        'metadata': {
            'n_nodes': G.number_of_nodes(),
            'n_edges': G.number_of_edges(),
            'n_communities': n_communities,
            'n_gaps': len(gaps),
            'god_nodes': god_nodes,
        }
    }

    graph_path = out_dir / 'graph.json'
    graph_path.write_text(json.dumps(graph_data, indent=2), encoding='utf-8')

    # confidence audit
    ext_c = sum(1 for e in all_edges if e.get('confidence') == 'EXTRACTED')
    inf_c = sum(1 for e in all_edges if e.get('confidence') == 'INFERRED')
    amb_c = sum(1 for e in all_edges if e.get('confidence') == 'AMBIGUOUS')
    total_e = len(all_edges) or 1

    print(f"Graph: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges, {n_communities} communities")
    print(f"Confidence: {ext_c/total_e*100:.0f}% EXTRACTED, {inf_c/total_e*100:.0f}% INFERRED, {amb_c/total_e*100:.0f}% AMBIGUOUS")
    print(f"God nodes: {god_nodes[:3]}")
    print(f"Knowledge gaps (isolated nodes): {len(gaps)}")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"ERROR:{e}", file=sys.stderr)
        sys.exit(1)
