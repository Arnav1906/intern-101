"""Graph data load/save and query operations for the visualise suite."""

import json
from pathlib import Path

from .utils import read_file, write_file

_GRAPH_FILENAME = "graph.json"
_EMPTY_GRAPH: dict = {"nodes": [], "edges": []}


def load_graph(visualise_out_dir: Path) -> dict:
    path = visualise_out_dir / _GRAPH_FILENAME
    raw = read_file(path)
    if not raw.strip():
        return {"nodes": [], "edges": []}
    try:
        data = json.loads(raw)
        if not isinstance(data, dict):
            return {"nodes": [], "edges": []}
        return {
            "nodes": data.get("nodes", []),
            "edges": data.get("edges", []),
        }
    except json.JSONDecodeError:
        return {"nodes": [], "edges": []}


def save_graph(graph: dict, visualise_out_dir: Path) -> None:
    path = visualise_out_dir / _GRAPH_FILENAME
    write_file(path, json.dumps(graph, indent=2))


def find_nodes(graph: dict, query: str) -> list[dict]:
    q = query.lower()
    scored = []
    for node in graph.get("nodes", []):
        fields = [
            str(node.get("id", "")),
            str(node.get("label", "")),
            str(node.get("description", "")),
        ]
        # rank: id match first, then label, then description
        rank = next(
            (i for i, f in enumerate(fields) if q in f.lower()),
            None,
        )
        if rank is not None:
            scored.append((rank, node))
    scored.sort(key=lambda x: x[0])
    return [node for _, node in scored]


def get_node(graph: dict, node_id: str) -> dict | None:
    for node in graph.get("nodes", []):
        if node.get("id") == node_id:
            return node
    return None


def get_neighbors(graph: dict, node_id: str) -> list[dict]:
    neighbor_ids = set()
    for edge in graph.get("edges", []):
        src = edge.get("source") or edge.get("from")
        tgt = edge.get("target") or edge.get("to")
        if src == node_id and tgt is not None:
            neighbor_ids.add(tgt)
        elif tgt == node_id and src is not None:
            neighbor_ids.add(src)
    return [n for n in graph.get("nodes", []) if n.get("id") in neighbor_ids]


def get_isolated_nodes(graph: dict) -> list[dict]:
    connected = set()
    for edge in graph.get("edges", []):
        src = edge.get("source") or edge.get("from")
        tgt = edge.get("target") or edge.get("to")
        if src:
            connected.add(src)
        if tgt:
            connected.add(tgt)
    return [n for n in graph.get("nodes", []) if n.get("id") not in connected]


def graph_stats(graph: dict) -> dict:
    nodes = graph.get("nodes", [])
    edges = graph.get("edges", [])
    communities = {n.get("community") for n in nodes if n.get("community") is not None}
    isolated = get_isolated_nodes(graph)
    return {
        "node_count": len(nodes),
        "edge_count": len(edges),
        "community_count": len(communities),
        "isolated_count": len(isolated),
    }
