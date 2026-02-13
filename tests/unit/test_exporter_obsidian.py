import json
from pathlib import Path

import pytest

from domain_models.manifest import DocumentTree, SummaryNode
from matome.exporters.obsidian import CanvasFile, ObsidianCanvasExporter


@pytest.fixture
def sample_tree() -> DocumentTree:
    """Create a sample DocumentTree with Root -> [Node A, Node B] -> [Chunk 1, Chunk 2]."""
    # Summary Nodes
    # node_a and node_b variables are unused but needed for the tree structure logic.
    # We assign them to avoid F841, or just instantiate inline if possible,
    # but they are referenced in children_indices of root.
    # Wait, they are NOT referenced in `all_nodes` anymore because I removed `all_nodes`.
    # So they are essentially dangling unless fetched by `store.get_node`.
    # BUT this fixture returns a DocumentTree that is supposed to be 'complete'.
    # If `all_nodes` is None, the tree object itself doesn't hold them.

    # To fix F841 and keep logic clear:
    # We can just define root and let the test mocks handle retrieval.
    # But `root` needs `children_indices`.

    root = SummaryNode(
        id="root",
        text="Root Summary",
        level=2,
        children_indices=["node_a", "node_b"],
    )

    # Mocking behavior where nodes are retrieved from store
    # Since generate_canvas_data uses _get_node which falls back to all_nodes if present,
    # we can keep all_nodes for this specific test fixture or mock store.
    # To test scalability changes properly, let's remove all_nodes and use store.

    # However, fixture signature returns DocumentTree. We need to mock store inside tests.

    return DocumentTree(
        root_node=root,
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
    canvas = CanvasFile(**data)
    assert len(canvas.nodes) == 1
    assert len(canvas.edges) == 1
    assert canvas.edges[0].from_node == "n1"  # Pydantic model uses snake_case


def test_generate_canvas_data(sample_tree: DocumentTree) -> None:
    """Test generating canvas data from a DocumentTree."""
    exporter = ObsidianCanvasExporter()

    # We must mock store because all_nodes is None
    from unittest.mock import MagicMock

    from domain_models.manifest import Chunk, SummaryNode

    store = MagicMock()

    # Reconstruct nodes for side effect
    node_a = SummaryNode(id="node_a", text="Summary A", level=1, children_indices=[0])
    node_b = SummaryNode(id="node_b", text="Summary B", level=1, children_indices=[1])
    root = sample_tree.root_node
    chunk0 = Chunk(index=0, text="C0", start_char_idx=0, end_char_idx=1)
    chunk1 = Chunk(index=1, text="C1", start_char_idx=2, end_char_idx=3)

    def get_node_side_effect(idx: int | str) -> Chunk | SummaryNode | None:
        if idx == "node_a":
            return node_a
        if idx == "node_b":
            return node_b
        if idx == "root":
            return root
        if idx == 0:
            return chunk0
        if idx == 1:
            return chunk1
        return None

    store.get_node.side_effect = get_node_side_effect

    canvas = exporter.generate_canvas_data(sample_tree, store=store)

    assert isinstance(canvas, CanvasFile)

    # We expect: Root, Node A, Node B, Chunk 1, Chunk 2 -> 5 nodes
    # Edges: Root->A, Root->B, A->Chunk1, B->Chunk2 -> 4 edges
    assert len(canvas.nodes) == 5
    assert len(canvas.edges) == 4

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

    # We must mock store because all_nodes is None
    from unittest.mock import MagicMock

    from domain_models.manifest import Chunk, SummaryNode

    store = MagicMock()

    # Reconstruct nodes for side effect
    node_a = SummaryNode(id="node_a", text="Summary A", level=1, children_indices=[0])
    node_b = SummaryNode(id="node_b", text="Summary B", level=1, children_indices=[1])
    root = sample_tree.root_node
    chunk0 = Chunk(index=0, text="C0", start_char_idx=0, end_char_idx=1)
    chunk1 = Chunk(index=1, text="C1", start_char_idx=2, end_char_idx=3)

    def get_node_side_effect(idx: int | str) -> Chunk | SummaryNode | None:
        if idx == "node_a":
            return node_a
        if idx == "node_b":
            return node_b
        if idx == "root":
            return root
        if idx == 0:
            return chunk0
        if idx == 1:
            return chunk1
        return None

    store.get_node.side_effect = get_node_side_effect

    exporter.export(sample_tree, output_file, store=store)

    assert output_file.exists()

    with output_file.open(encoding="utf-8") as f:
        data = json.load(f)

    assert "nodes" in data
    assert "edges" in data
    # Verify serialization alias
    assert "fromNode" in data["edges"][0]
    assert "toNode" in data["edges"][0]
