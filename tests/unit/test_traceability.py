from unittest.mock import MagicMock

import pytest

from domain_models.config import ProcessingConfig
from domain_models.manifest import Chunk, NodeMetadata, SummaryNode
from matome.engines.interactive_raptor import InteractiveRaptorEngine


@pytest.fixture
def mock_store() -> MagicMock:
    return MagicMock()


@pytest.fixture
def interactive_engine(mock_store: MagicMock) -> InteractiveRaptorEngine:
    config = ProcessingConfig()
    return InteractiveRaptorEngine(store=mock_store, summarizer=None, config=config)


def test_get_source_chunks_direct_children(interactive_engine: InteractiveRaptorEngine, mock_store: MagicMock) -> None:
    """Test retrieving chunks when they are direct children."""
    summary_node = SummaryNode(
        id="s1",
        text="Summary",
        level=1,
        children_indices=[1, 2],
        metadata=NodeMetadata(),
    )
    c1 = Chunk(index=1, text="C1", start_char_idx=0, end_char_idx=2)
    c2 = Chunk(index=2, text="C2", start_char_idx=3, end_char_idx=5)

    mock_store.get_node.return_value = summary_node
    # When get_nodes is called with [1, 2], return [c1, c2]
    mock_store.get_nodes.return_value = iter([c1, c2])

    chunks = interactive_engine.get_source_chunks("s1")

    assert len(chunks) == 2
    assert c1 in chunks
    assert c2 in chunks


def test_get_source_chunks_nested(interactive_engine: InteractiveRaptorEngine, mock_store: MagicMock) -> None:
    """Test retrieving chunks from a deeper level."""
    # Root -> Child Summary -> [Chunk1, Chunk2]
    root = SummaryNode(
        id="root",
        text="Root",
        level=2,
        children_indices=["child"],
        metadata=NodeMetadata(),
    )
    child = SummaryNode(
        id="child",
        text="Child",
        level=1,
        children_indices=[1, 2],
        metadata=NodeMetadata(),
    )
    c1 = Chunk(index=1, text="C1", start_char_idx=0, end_char_idx=2)
    c2 = Chunk(index=2, text="C2", start_char_idx=3, end_char_idx=5)

    # Setup get_node responses
    def get_node_side_effect(nid: str | int) -> SummaryNode | Chunk | None:
        if nid == "root":
            return root
        if nid == "child":
            return child
        return None

    mock_store.get_node.side_effect = get_node_side_effect

    # Setup get_nodes responses for traversal
    # First call: root children -> [child]
    # Second call: child children -> [c1, c2]
    mock_store.get_nodes.side_effect = [
        iter([child]),
        iter([c1, c2])
    ]

    chunks = interactive_engine.get_source_chunks("root")

    assert len(chunks) == 2
    assert c1 in chunks
    assert c2 in chunks


def test_get_source_chunks_mixed(interactive_engine: InteractiveRaptorEngine, mock_store: MagicMock) -> None:
    """Test retrieving chunks from a node having both SummaryNode and Chunk children (if possible)."""
    # Root -> [Child Summary, Chunk3]
    # Child Summary -> [Chunk1, Chunk2]
    root = SummaryNode(
        id="root",
        text="Root",
        level=2,
        children_indices=["child", 3],
        metadata=NodeMetadata(),
    )
    child = SummaryNode(
        id="child",
        text="Child",
        level=1,
        children_indices=[1, 2],
        metadata=NodeMetadata(),
    )
    c1 = Chunk(index=1, text="C1", start_char_idx=0, end_char_idx=2)
    c2 = Chunk(index=2, text="C2", start_char_idx=3, end_char_idx=5)
    c3 = Chunk(index=3, text="C3", start_char_idx=6, end_char_idx=8)

    mock_store.get_node.side_effect = lambda nid: root if nid == "root" else child

    # First call for root's children
    # Second call for child's children
    mock_store.get_nodes.side_effect = [
        iter([child, c3]),
        iter([c1, c2])
    ]

    chunks = interactive_engine.get_source_chunks("root")

    assert len(chunks) == 3
    assert c1 in chunks
    assert c2 in chunks
    assert c3 in chunks


def test_get_source_chunks_node_not_found(interactive_engine: InteractiveRaptorEngine, mock_store: MagicMock) -> None:
    mock_store.get_node.return_value = None
    chunks = interactive_engine.get_source_chunks("missing")
    assert chunks == []


def test_get_source_chunks_from_chunk(interactive_engine: InteractiveRaptorEngine, mock_store: MagicMock) -> None:
    """If called on a chunk ID, it should return that chunk."""
    c1 = Chunk(index=1, text="C1", start_char_idx=0, end_char_idx=2)
    mock_store.get_node.return_value = c1

    chunks = interactive_engine.get_source_chunks(1)

    assert len(chunks) == 1
    assert chunks[0] == c1
