from unittest.mock import MagicMock

import pytest

from domain_models.manifest import Chunk, DocumentTree, SummaryNode
from domain_models.metadata import DIKWLevel, NodeMetadata
from domain_models.types import NodeID
from matome.exporters.obsidian import CanvasEdge, CanvasFile, CanvasNode, ObsidianCanvasExporter


@pytest.fixture
def mock_tree() -> DocumentTree:
    # Root Summary (Wisdom)
    root = SummaryNode(
        id="root",
        text="Root Wisdom",
        level=2,
        children_indices=["summary1", "summary2"],
        metadata=NodeMetadata(dikw_level=DIKWLevel.WISDOM)
    )

    # Knowledge Nodes
    summary1 = SummaryNode(
        id="summary1",
        text="Knowledge A",
        level=1,
        children_indices=[0, 1], # Chunks
        metadata=NodeMetadata(dikw_level=DIKWLevel.KNOWLEDGE)
    )

    summary2 = SummaryNode(
        id="summary2",
        text="Knowledge B",
        level=1,
        children_indices=[2], # Chunks
        metadata=NodeMetadata(dikw_level=DIKWLevel.KNOWLEDGE)
    )

    all_summaries = {"summary1": summary1, "summary2": summary2, "root": root}
    # Explicitly type leaf_ids as list[NodeID] which is list[int | str]
    leaf_ids: list[NodeID] = [0, 1, 2]

    return DocumentTree(
        root_node=root,
        all_nodes=all_summaries,
        leaf_chunk_ids=leaf_ids,
        metadata={"levels": 2}
    )

@pytest.fixture
def mock_store() -> MagicMock:
    store = MagicMock()

    def get_node(nid: NodeID) -> Chunk | None:
        if nid == 0:
            return Chunk(index=0, text="Chunk 0", start_char_idx=0, end_char_idx=10)
        if nid == 1:
            return Chunk(index=1, text="Chunk 1", start_char_idx=10, end_char_idx=20)
        if nid == 2:
            return Chunk(index=2, text="Chunk 2", start_char_idx=20, end_char_idx=30)
        return None

    store.get_node.side_effect = get_node
    return store

def test_canvas_export_structure(mock_tree: DocumentTree, mock_store: MagicMock) -> None:
    exporter = ObsidianCanvasExporter()
    canvas = exporter.generate_canvas_data(mock_tree, mock_store)

    assert isinstance(canvas, CanvasFile)
    assert len(canvas.nodes) > 0
    assert len(canvas.edges) > 0

    # Root + 2 summaries + 3 chunks = 6 nodes
    assert len(canvas.nodes) == 6

    # Root->Summary (2 edges) + Summary->Chunks (3 edges) = 5 edges
    assert len(canvas.edges) == 5

    # Check Edge properties
    edge = canvas.edges[0]
    # We used alias in definition, but standard field name is from_node
    # Pydantic populates standard field name too if populate_by_name=True
    assert hasattr(edge, "from_node")
    assert hasattr(edge, "to_node")


def test_canvas_edge_creation() -> None:
    # Test manual edge creation with alias
    # mypy requires alias kwarg if using alias?
    edge = CanvasEdge(
        id="test_edge",
        fromNode="node1",
        toNode="node2"
    )
    assert edge.from_node == "node1"
    assert edge.to_node == "node2"

    # Test dumping
    dump = edge.model_dump(by_alias=True)
    assert "fromNode" in dump
    assert "toNode" in dump


def test_canvas_file_creation() -> None:
    node1 = CanvasNode(id="n1", x=0, y=0, width=100, height=100, text="Node 1")
    node2 = CanvasNode(id="n2", x=200, y=0, width=100, height=100, text="Node 2")
    edge = CanvasEdge(id="e1", fromNode="n1", toNode="n2")

    canvas_file = CanvasFile(
        nodes=[node1, node2],
        edges=[edge]
    )

    assert len(canvas_file.nodes) == 2
    assert len(canvas_file.edges) == 1
