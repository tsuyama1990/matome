from unittest.mock import MagicMock

import pytest

from domain_models.data_schema import NodeMetadata
from domain_models.manifest import Chunk, SummaryNode
from matome.engines.interactive_raptor import InteractiveRaptorEngine
from matome.utils.store import DiskChunkStore


@pytest.fixture
def mock_store() -> MagicMock:
    return MagicMock(spec=DiskChunkStore)


@pytest.fixture
def engine(mock_store: MagicMock) -> InteractiveRaptorEngine:
    return InteractiveRaptorEngine(store=mock_store, agent=MagicMock())


def test_get_children_summary_nodes(engine: InteractiveRaptorEngine, mock_store: MagicMock) -> None:
    """Test retrieving children that are SummaryNodes."""
    # Parent node
    parent = SummaryNode(
        id="p1", text="Parent", level=2, children_indices=["c1", "c2"], metadata=NodeMetadata()
    )
    mock_store.get_node.return_value = parent

    # Children nodes
    child1 = SummaryNode(
        id="c1", text="Child 1", level=1, children_indices=["leaf1"], metadata=NodeMetadata()
    )
    child2 = SummaryNode(
        id="c2", text="Child 2", level=1, children_indices=["leaf2"], metadata=NodeMetadata()
    )

    # Mock batch retrieval
    mock_store.get_nodes.return_value = {"c1": child1, "c2": child2}

    children = engine.get_children("p1")

    assert len(children) == 2
    assert child1 in children
    assert child2 in children
    mock_store.get_nodes.assert_called_with(["c1", "c2"])


def test_get_children_chunks(engine: InteractiveRaptorEngine, mock_store: MagicMock) -> None:
    """Test retrieving children that are Chunks."""
    parent = SummaryNode(
        id="p1", text="Parent", level=1, children_indices=[1, 2], metadata=NodeMetadata()
    )
    mock_store.get_node.return_value = parent

    chunk1 = Chunk(index=1, text="C1", start_char_idx=0, end_char_idx=2)
    chunk2 = Chunk(index=2, text="C2", start_char_idx=3, end_char_idx=5)

    # Mock batch retrieval. Note: keys can be int or str(int) depending on implementation details
    # Engine passes [1, 2] to get_nodes. Store returns dict with keys matching input type.
    mock_store.get_nodes.return_value = {1: chunk1, 2: chunk2}

    children = engine.get_children("p1")

    assert len(children) == 2
    assert chunk1 in children
    assert chunk2 in children
    mock_store.get_nodes.assert_called_with([1, 2])


def test_get_source_chunks(engine: InteractiveRaptorEngine, mock_store: MagicMock) -> None:
    """Test recursive retrieval of source chunks."""
    # Tree Structure:
    # Root (L2) -> [Child1 (L1), Child2 (L1)]
    # Child1 -> [Leaf1 (L0), Leaf2 (L0)]
    # Child2 -> [Leaf3 (L0)]

    root = SummaryNode(
        id="root", text="Root", level=2, children_indices=["c1", "c2"], metadata=NodeMetadata()
    )
    child1 = SummaryNode(
        id="c1", text="C1", level=1, children_indices=[1, 2], metadata=NodeMetadata()
    )
    child2 = SummaryNode(id="c2", text="C2", level=1, children_indices=[3], metadata=NodeMetadata())

    leaf1 = Chunk(index=1, text="L1", start_char_idx=0, end_char_idx=1)
    leaf2 = Chunk(index=2, text="L2", start_char_idx=2, end_char_idx=3)
    leaf3 = Chunk(index=3, text="L3", start_char_idx=4, end_char_idx=5)

    # Setup mock_store.get_node to return root initially
    mock_store.get_node.return_value = root

    # Setup mock_store.get_nodes to handle batches
    # 1. First call: get children of Root -> ["c1", "c2"]
    # 2. Next calls: get children of c1 -> [1, 2], get children of c2 -> [3]

    def get_nodes_side_effect(ids: list[str | int]) -> dict[str | int, SummaryNode | Chunk | None]:
        results: dict[str | int, SummaryNode | Chunk | None] = {}
        for nid in ids:
            if nid == "c1":
                results["c1"] = child1
            elif nid == "c2":
                results["c2"] = child2
            elif nid == 1:
                results[1] = leaf1
            elif nid == 2:
                results[2] = leaf2
            elif nid == 3:
                results[3] = leaf3
        return results

    mock_store.get_nodes.side_effect = get_nodes_side_effect

    sources = engine.get_source_chunks("root")

    # Order might vary depending on traversal (BFS/DFS), but all leaves must be present
    assert len(sources) == 3
    chunk_texts = {c.text for c in sources}
    assert chunk_texts == {"L1", "L2", "L3"}
