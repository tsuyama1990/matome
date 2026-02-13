import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from domain_models.data_schema import DIKWLevel, NodeMetadata
from domain_models.manifest import Chunk, DocumentTree, SummaryNode
from matome.exporters.obsidian import CanvasFile, ObsidianCanvasExporter


@pytest.fixture
def sample_tree() -> DocumentTree:
    """Create a sample DocumentTree with Root -> [Node A, Node B] -> [Chunk 1, Chunk 2]."""
    root = SummaryNode(
        id="root",
        text="Root Summary",
        level=2,
        children_indices=["node_a", "node_b"],
        metadata=NodeMetadata(dikw_level=DIKWLevel.WISDOM),
    )

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
    canvas = CanvasFile(**data)
    assert len(canvas.nodes) == 1
    assert len(canvas.edges) == 1
    assert canvas.edges[0].from_node == "n1"  # Pydantic model uses snake_case


def test_generate_canvas_data(sample_tree: DocumentTree) -> None:
    """Test generating canvas data from a DocumentTree."""
    exporter = ObsidianCanvasExporter()

    store = MagicMock()

    # Reconstruct nodes for side effect
    node_a = SummaryNode(
        id="node_a",
        text="Summary A",
        level=1,
        children_indices=[0],
        metadata=NodeMetadata(dikw_level=DIKWLevel.KNOWLEDGE),
    )
    node_b = SummaryNode(
        id="node_b",
        text="Summary B",
        level=1,
        children_indices=[1],
        metadata=NodeMetadata(dikw_level=DIKWLevel.KNOWLEDGE),
    )
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

    # We expect: Root, Node A, Node B, Chunk 0, Chunk 1 -> 5 nodes
    # Edges: Root->A, Root->B, A->Chunk0, B->Chunk1 -> 4 edges

    assert len(canvas.nodes) == 5
    assert len(canvas.edges) == 4

    # Check Root Position (should be top)
    root_node = next(n for n in canvas.nodes if n.id == "root")
    assert root_node.y == 0

    # Check Children Y position (should be below root)
    child_a = next(n for n in canvas.nodes if n.id == "node_a")
    child_b = next(n for n in canvas.nodes if n.id == "node_b")

    # Spec says "Children go to y + 400" (or similar default height/gap)
    assert child_a.y > root_node.y
    assert child_b.y > root_node.y

    # Check Children X position (should be spread out)
    assert child_a.x != child_b.x

    # Check Chunk Y position (should be below parents)
    # Check for chunk nodes by prefix "chunk_"
    chunk_0_node = next(n for n in canvas.nodes if n.id == "chunk_0")
    chunk_1_node = next(n for n in canvas.nodes if n.id == "chunk_1")

    assert chunk_0_node.y > child_a.y
    assert chunk_1_node.y > child_b.y


def test_export_file(sample_tree: DocumentTree, tmp_path: Path) -> None:
    """Test exporting to a file."""
    exporter = ObsidianCanvasExporter()
    output_file = tmp_path / "test.canvas"

    store = MagicMock()

    # Reconstruct nodes for side effect
    node_a = SummaryNode(
        id="node_a",
        text="Summary A",
        level=1,
        children_indices=[0],
        metadata=NodeMetadata(dikw_level=DIKWLevel.KNOWLEDGE),
    )
    node_b = SummaryNode(
        id="node_b",
        text="Summary B",
        level=1,
        children_indices=[1],
        metadata=NodeMetadata(dikw_level=DIKWLevel.KNOWLEDGE),
    )
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
