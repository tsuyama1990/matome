import json
from pathlib import Path

import pytest

from domain_models.manifest import DocumentTree, SummaryNode
from matome.exporters.obsidian import CanvasFile, ObsidianCanvasExporter


@pytest.fixture
def sample_tree() -> DocumentTree:
    """Create a sample DocumentTree with Root -> [Node A, Node B] -> [Chunk 1, Chunk 2]."""
    # Summary Nodes
    node_a = SummaryNode(
        id="node_a",
        text="Summary A",
        level=1,
        children_indices=[0],  # Points to Chunk 0
    )
    node_b = SummaryNode(
        id="node_b",
        text="Summary B",
        level=1,
        children_indices=[1],  # Points to Chunk 1
    )
    root = SummaryNode(
        id="root",
        text="Root Summary",
        level=2,
        children_indices=["node_a", "node_b"],
    )

    all_nodes = {
        "root": root,
        "node_a": node_a,
        "node_b": node_b,
    }

    return DocumentTree(
        root_node=root,
        all_nodes=all_nodes,
        leaf_chunk_ids=[0, 1],
    )


def test_canvas_schema_validation() -> None:
    """Test that CanvasFile enforces schema."""
    # Valid
    data = {
        "nodes": [
            {
                "id": "n1",
                "x": 0,
                "y": 0,
                "width": 100,
                "height": 100,
                "type": "text",
                "text": "Hello",
            }
        ],
        "edges": [{"id": "e1", "fromNode": "n1", "toNode": "n2"}],
    }
    # We expect validation error on missing 'toNode' target if we were validating logic,
    # but here just schema. 'n2' doesn't exist in nodes but edge is valid schema-wise.
    canvas = CanvasFile.model_validate(data)
    assert len(canvas.nodes) == 1
    assert len(canvas.edges) == 1
    assert canvas.edges[0].from_node == "n1"  # Pydantic model uses snake_case


def test_generate_canvas_data(sample_tree: DocumentTree) -> None:
    """Test generating canvas data from a DocumentTree."""
    exporter = ObsidianCanvasExporter()
    canvas = exporter.generate_canvas_data(sample_tree)

    assert isinstance(canvas, CanvasFile)

    # We expect: Root, Node A, Node B, Chunk 1, Chunk 2
    # Verify structural presence instead of exact count if implementation adds auxiliary nodes (unlikely here but good practice)
    node_ids = {n.id for n in canvas.nodes}
    assert "root" in node_ids
    assert "node_a" in node_ids
    assert "node_b" in node_ids
    # Check that chunks are present (IDs starting with chunk_)
    assert any(nid.startswith("chunk_") for nid in node_ids)

    # Check Edges exist
    edge_pairs = {(e.from_node, e.to_node) for e in canvas.edges}
    assert ("root", "node_a") in edge_pairs
    assert ("root", "node_b") in edge_pairs

    # Check Root Position (should be top)
    root_node = next(n for n in canvas.nodes if n.id == "root")
    assert root_node.y == 0
    # Root should be centered at x=0. Width=400 -> x=-200
    assert root_node.x == -(root_node.width // 2)

    # Check Children Y position (should be below root)
    child_a = next(n for n in canvas.nodes if n.id == "node_a")
    child_b = next(n for n in canvas.nodes if n.id == "node_b")

    # Spec says "Children go to y + 400"
    assert child_a.y > root_node.y
    assert child_b.y > root_node.y

    # Check Children X position (should be spread out)
    assert child_a.x != child_b.x

    # Check Chunk Y position (should be below parents)
    chunk_1 = next(n for n in canvas.nodes if n.id.startswith("chunk_"))
    assert chunk_1.y > child_a.y

    # Check Edge connections
    edge_root_a = next(e for e in canvas.edges if e.from_node == "root" and e.to_node == "node_a")
    assert edge_root_a is not None


def test_export_file(sample_tree: DocumentTree, tmp_path: Path) -> None:
    """Test exporting to a file."""
    exporter = ObsidianCanvasExporter()
    output_file = tmp_path / "test.canvas"

    exporter.export(sample_tree, output_file)

    assert output_file.exists()

    with output_file.open(encoding="utf-8") as f:
        data = json.load(f)

    assert "nodes" in data
    assert "edges" in data
    # Verify serialization alias
    assert "fromNode" in data["edges"][0]
    assert "toNode" in data["edges"][0]
