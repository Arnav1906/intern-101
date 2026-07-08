import json
import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).parent.parent / "scripts" / "visualise" / "report.py"
PYTHON = sys.executable


def _make_graph(tmp_path: Path, nodes: list, edges: list) -> Path:
    out = tmp_path / "visualise-out"
    out.mkdir()
    (out / "graph.json").write_text(
        json.dumps({"nodes": nodes, "edges": edges}), encoding="utf-8"
    )
    return out


def _run(args: list, cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [PYTHON, str(SCRIPT)] + args,
        capture_output=True, text=True, cwd=str(cwd)
    )


def test_report_generates_file(tmp_path):
    """report.py writes GRAPH_REPORT.md and prints WRITTEN:<path>."""
    _make_graph(tmp_path, [
        {"id": "foo", "label": "Foo", "type": "module", "description": "Does foo", "community": 0, "confidence": "EXTRACTED"},
    ], [])
    result = _run([], tmp_path)
    assert result.returncode == 0, result.stderr
    assert "WRITTEN:" in result.stdout
    assert (tmp_path / "visualise-out" / "GRAPH_REPORT.md").exists()


def test_report_has_both_sections(tmp_path):
    """Output contains Architecture by Cluster and Node Reference sections."""
    _make_graph(tmp_path, [
        {"id": "a", "label": "A", "type": "function", "description": "Alpha", "community": 0, "confidence": "EXTRACTED"},
        {"id": "b", "label": "B", "type": "function", "description": "Beta",  "community": 1, "confidence": "EXTRACTED"},
    ], [{"source": "a", "target": "b", "label": "calls", "weight": 1.0}])
    _run([], tmp_path)
    content = (tmp_path / "visualise-out" / "GRAPH_REPORT.md").read_text(encoding="utf-8")
    assert "## Architecture by Cluster" in content
    assert "## Node Reference" in content


def test_report_handles_missing_community(tmp_path):
    """Nodes without a community field are grouped as 'unclustered'."""
    _make_graph(tmp_path, [
        {"id": "x", "label": "X", "type": "module", "description": "No community"},
    ], [])
    _run([], tmp_path)
    content = (tmp_path / "visualise-out" / "GRAPH_REPORT.md").read_text(encoding="utf-8")
    assert "unclustered" in content.lower()


def test_report_empty_graph_exits_error(tmp_path):
    """Exit code 1 and ERROR: on stderr when graph has no nodes."""
    out = tmp_path / "visualise-out"
    out.mkdir()
    (out / "graph.json").write_text(json.dumps({"nodes": [], "edges": []}), encoding="utf-8")
    result = _run([], tmp_path)
    assert result.returncode == 1
    assert "ERROR:" in result.stderr


def test_report_missing_graph_exits_error(tmp_path):
    """Exit code 1 and ERROR: when graph.json does not exist."""
    result = _run([], tmp_path)
    assert result.returncode == 1
    assert "ERROR:" in result.stderr


def test_report_custom_path(tmp_path):
    """--path flag points to a non-default graph.json location."""
    custom = tmp_path / "custom-out"
    custom.mkdir()
    (custom / "graph.json").write_text(
        json.dumps({"nodes": [{"id": "z", "label": "Z", "type": "class", "description": "Zed", "community": 0, "confidence": "INFERRED"}], "edges": []}),
        encoding="utf-8"
    )
    result = _run(["--path", str(custom / "graph.json")], tmp_path)
    assert result.returncode == 0
    assert (custom / "GRAPH_REPORT.md").exists()


def test_report_cross_cluster_edges_in_section1(tmp_path):
    """Cross-cluster edges appear under Architecture by Cluster."""
    _make_graph(tmp_path, [
        {"id": "p", "label": "P", "type": "module", "description": "P desc", "community": 0, "confidence": "EXTRACTED"},
        {"id": "q", "label": "Q", "type": "module", "description": "Q desc", "community": 1, "confidence": "EXTRACTED"},
    ], [{"source": "p", "target": "q", "label": "imports", "weight": 1.0}])
    _run([], tmp_path)
    content = (tmp_path / "visualise-out" / "GRAPH_REPORT.md").read_text(encoding="utf-8")
    assert "p → q" in content


def test_report_node_reference_top3_connections(tmp_path):
    """Each node in Section 2 shows at most 3 connections."""
    nodes = [{"id": str(i), "label": str(i), "type": "fn", "description": "", "community": 0, "confidence": "EXTRACTED"} for i in range(5)]
    edges = [{"source": "0", "target": str(i), "label": "calls", "weight": 1.0} for i in range(1, 5)]
    _make_graph(tmp_path, nodes, edges)
    _run([], tmp_path)
    content = (tmp_path / "visualise-out" / "GRAPH_REPORT.md").read_text(encoding="utf-8")
    node_ref = content.split("## Node Reference")[-1]
    node_block = node_ref.split("### 0")[-1].split("###")[0]
    connections_line = [l for l in node_block.splitlines() if l.startswith("Connections:")]
    assert len(connections_line) == 1
    assert connections_line[0].count(",") <= 2  # at most 3 items = at most 2 commas
