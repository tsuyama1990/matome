from unittest.mock import MagicMock

import pytest

from domain_models.config import ProcessingConfig
from domain_models.manifest import Chunk, NodeMetadata, SummaryNode
from domain_models.types import DIKWLevel
from matome.engines.interactive_raptor import InteractiveRaptorEngine


@pytest.fixture
def mock_store() -> MagicMock:
    return MagicMock()


@pytest.fixture
def mock_summarizer() -> MagicMock:
    summarizer = MagicMock()
    summarizer.summarize.return_value = "Refined Summary"
    return summarizer


@pytest.fixture
def interactive_engine(
    mock_store: MagicMock, mock_summarizer: MagicMock
) -> InteractiveRaptorEngine:
    config = ProcessingConfig()
    return InteractiveRaptorEngine(store=mock_store, summarizer=mock_summarizer, config=config)


def test_refine_node_success(
    interactive_engine: InteractiveRaptorEngine,
    mock_store: MagicMock,
    mock_summarizer: MagicMock,
) -> None:
    # Arrange
    node_id = "summary_1"
    child_chunk = Chunk(
        index=1, text="Child Text", start_char_idx=0, end_char_idx=10, embedding=[0.1]
    )
    summary_node = SummaryNode(
        id=node_id,
        text="Original Summary",
        level=1,
        children_indices=[1],
        metadata=NodeMetadata(dikw_level=DIKWLevel.WISDOM),
    )

    def get_node_side_effect(nid: int | str) -> SummaryNode | Chunk | None:
        if nid == node_id:
            return summary_node
        if nid == 1:
            return child_chunk
        return None

    mock_store.get_node.side_effect = get_node_side_effect

    instruction = "Make it shorter"

    # Act
    refined_node = interactive_engine.refine_node(node_id, instruction)

    # Assert
    assert refined_node.text == "Refined Summary"
    assert refined_node.metadata.is_user_edited is True
    assert instruction in refined_node.metadata.refinement_history

    # Check that summarizer was called with correct context
    args, kwargs = mock_summarizer.summarize.call_args
    assert kwargs["context"]["instruction"] == instruction
    # Check that store.add_summary was called to save changes
    mock_store.add_summary.assert_called_once_with(summary_node)


def test_refine_node_not_found(interactive_engine: InteractiveRaptorEngine, mock_store: MagicMock) -> None:
    mock_store.get_node.return_value = None
    with pytest.raises(ValueError, match="Node missing not found"):
        interactive_engine.refine_node("missing", "instruction")


def test_refine_node_chunk_error(
    interactive_engine: InteractiveRaptorEngine, mock_store: MagicMock
) -> None:
    chunk = Chunk(index=1, text="Chunk", start_char_idx=0, end_char_idx=5)
    mock_store.get_node.return_value = chunk
    with pytest.raises(TypeError, match="Only SummaryNodes can be refined"):
        interactive_engine.refine_node("1", "instruction")


def test_get_children(
    interactive_engine: InteractiveRaptorEngine, mock_store: MagicMock
) -> None:
    # Arrange
    summary_node = SummaryNode(
        id="s1",
        text="Summary",
        level=1,
        children_indices=[1, 2],
        metadata=NodeMetadata(),
    )
    c1 = Chunk(index=1, text="C1", start_char_idx=0, end_char_idx=2)
    c2 = Chunk(index=2, text="C2", start_char_idx=3, end_char_idx=5)

    mock_store.get_node.side_effect = lambda nid: {1: c1, 2: c2}.get(nid)

    # Act
    children = interactive_engine.get_children(summary_node)

    # Assert
    assert len(children) == 2
    assert c1 in children
    assert c2 in children
