import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from domain_models.manifest import Chunk, DocumentTree, NodeMetadata, SummaryNode
from domain_models.types import DIKWLevel
from matome.exporters.obsidian import CanvasFile, ObsidianCanvasExporter


@pytest.fixture
def nodes_and_chunks() -> tuple[dict[int | str, Chunk | SummaryNode], SummaryNode]:
    # Summary Nodes
    node_a = SummaryNode(
        id="node_a",
        text="Summary A",
        level=1,
        children_indices=[0],  # Points to Chunk 0
        metadata=NodeMetadata(dikw_level=DIKWLevel.INFORMATION)
    )
    node_b = SummaryNode(
        id="node_b",
        text="Summary B",
        level=1,
        children_indices=[1],  # Points to Chunk 1
        metadata=NodeMetadata(dikw_level=DIKWLevel.INFORMATION)
    )
    root = SummaryNode(
        id="root",
        text="Root Summary",
        level=2,
        children_indices=["node_a", "node_b"],
        metadata=NodeMetadata(dikw_level=DIKWLevel.WISDOM)
    )

    chunk0 = Chunk(index=0, text="Chunk 0", start_char_idx=0, end_char_idx=10)
    chunk1 = Chunk(index=1, text="Chunk 1", start_char_idx=10, end_char_idx=20)

    all_nodes: dict[int | str, Chunk | SummaryNode] = {
        "root": root,
        "node_a": node_a,
        "node_b": node_b,
        0: chunk0,
        1: chunk1
    }

    return all_nodes, root

@pytest.fixture
def sample_tree(nodes_and_chunks: tuple[dict[int | str, Chunk | SummaryNode], SummaryNode]) -> DocumentTree:
    _, root = nodes_and_chunks
    return DocumentTree(
        root_node=root,
        leaf_chunk_ids=[0, 1],
    )

@pytest.fixture
def mock_store(nodes_and_chunks: tuple[dict[int | str, Chunk | SummaryNode], SummaryNode]) -> MagicMock:
    all_nodes, _ = nodes_and_chunks
    store = MagicMock()
    store.get_node.side_effect = all_nodes.get
    return store


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


def test_generate_canvas_data(sample_tree: DocumentTree, mock_store: MagicMock) -> None:
    """Test generating canvas data from a DocumentTree."""
    exporter = ObsidianCanvasExporter()
    canvas = exporter.generate_canvas_data(sample_tree, mock_store)

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

    # Spec says "Children go to y + 400" or similar based on GAP_Y
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


def test_export_file(sample_tree: DocumentTree, mock_store: MagicMock, tmp_path: Path) -> None:
    """Test exporting to a file."""
    exporter = ObsidianCanvasExporter()
    output_file = tmp_path / "test.canvas"

    exporter.export(sample_tree, output_file, mock_store)

    assert output_file.exists()

    with output_file.open(encoding="utf-8") as f:
        data = json.load(f)

    assert "nodes" in data
    assert "edges" in data
    # Verify serialization alias
    assert "fromNode" in data["edges"][0]
    assert "toNode" in data["edges"][0]
