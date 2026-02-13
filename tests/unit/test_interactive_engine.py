from unittest.mock import MagicMock

import pytest

from domain_models.data_schema import DIKWLevel, NodeMetadata
from domain_models.manifest import Chunk, SummaryNode
from matome.agents.strategies import RefinementStrategy, WisdomStrategy
from matome.engines.interactive_raptor import InteractiveRaptorEngine


@pytest.fixture
def mock_store() -> MagicMock:
    return MagicMock()


@pytest.fixture
def mock_agent() -> MagicMock:
    return MagicMock()


@pytest.fixture
def engine(mock_store: MagicMock, mock_agent: MagicMock) -> InteractiveRaptorEngine:
    return InteractiveRaptorEngine(mock_store, mock_agent)


def test_get_children(engine: InteractiveRaptorEngine, mock_store: MagicMock) -> None:
    parent = SummaryNode(
        id="p1",
        text="Parent",
        level=2,
        children_indices=["c1", 0],
        metadata=NodeMetadata(dikw_level=DIKWLevel.KNOWLEDGE),
    )
    c1 = SummaryNode(
        id="c1",
        text="Child 1",
        level=1,
        children_indices=[],
        metadata=NodeMetadata(dikw_level=DIKWLevel.INFORMATION),
    )
    c2 = Chunk(index=0, text="Chunk 0", start_char_idx=0, end_char_idx=5)

    def get_node_side_effect(nid: int | str) -> Chunk | SummaryNode | None:
        if nid == "p1":
            return parent
        if nid == "c1":
            return c1
        if nid == 0:
            return c2
        return None

    mock_store.get_node.side_effect = get_node_side_effect

    children = engine.get_children("p1")
    assert len(children) == 2

    # Fix: Assert types to satisfy mypy
    child0 = children[0]
    child1 = children[1]

    assert isinstance(child0, SummaryNode)
    assert child0.id == "c1"

    assert isinstance(child1, Chunk)
    assert child1.index == 0


def test_refine_node(
    engine: InteractiveRaptorEngine, mock_store: MagicMock, mock_agent: MagicMock
) -> None:
    node = SummaryNode(
        id="n1",
        text="Original",
        level=1,
        children_indices=[0],
        metadata=NodeMetadata(dikw_level=DIKWLevel.WISDOM),
    )
    child = Chunk(index=0, text="Source text", start_char_idx=0, end_char_idx=10)

    def get_node_side_effect(nid: int | str) -> Chunk | SummaryNode | None:
        if nid == "n1":
            return node
        if nid == 0:
            return child
        return None

    mock_store.get_node.side_effect = get_node_side_effect

    # Mock agent response
    new_node = SummaryNode(
        id="new_id",
        text="Refined Wisdom",
        level=1,
        children_indices=[0],
        metadata=NodeMetadata(
            dikw_level=DIKWLevel.WISDOM,
            is_user_edited=True,
            refinement_history=["Make it wiser"],
        ),
    )
    mock_agent.summarize.return_value = new_node

    result = engine.refine_node("n1", "Make it wiser")

    # Assertions
    assert result.text == "Refined Wisdom"
    assert result.metadata.is_user_edited

    # Verify agent call
    mock_agent.summarize.assert_called_once()
    args, kwargs = mock_agent.summarize.call_args
    assert kwargs["context"]["instruction"] == "Make it wiser"
    strategy = kwargs["strategy"]
    assert isinstance(strategy, RefinementStrategy)
    assert isinstance(strategy.base_strategy, WisdomStrategy)

    # Verify store update
    mock_store.add_summary.assert_called_with(new_node)
