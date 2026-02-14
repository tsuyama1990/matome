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

    # Use iterator for get_nodes return to simulate streaming
    mock_store.get_node.return_value = summary_node
    mock_store.get_nodes.return_value = iter([child_chunk])
    # Mock transaction context manager
    mock_store.transaction.return_value.__enter__.return_value = MagicMock()

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
    # Check that store.update_node was called to save changes
    mock_store.update_node.assert_called_once_with(summary_node)


def test_refine_node_not_found(interactive_engine: InteractiveRaptorEngine, mock_store: MagicMock) -> None:
    mock_store.get_node.return_value = None
    with pytest.raises(ValueError, match="Node .* not found"):
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

    # get_nodes returns iterator
    mock_store.get_nodes.return_value = iter([c1, c2])

    # Act
    children_iter = interactive_engine.get_children(summary_node)

    # Assert return type is iterator
    assert iter(children_iter) is children_iter

    # Materialize to check content
    children = list(children_iter)
    assert len(children) == 2
    assert c1 in children
    assert c2 in children
    mock_store.get_nodes.assert_called_once()


def test_refine_node_invalid_instruction(
    interactive_engine: InteractiveRaptorEngine, mock_store: MagicMock
) -> None:
    """Test that refining with invalid instruction raises ValueError."""
    # Setup a valid node
    node = SummaryNode(
        id="s1",
        text="Summary",
        level=1,
        children_indices=[1],
        metadata=NodeMetadata()
    )
    mock_store.get_node.return_value = node

    # Test empty instruction
    with pytest.raises(ValueError, match="Instruction cannot be empty"):
        interactive_engine.refine_node("s1", "")

    # Test whitespace-only instruction
    with pytest.raises(ValueError, match="Instruction cannot be empty"):
        interactive_engine.refine_node("s1", "   ")

    # Test too long instruction
    long_instruction = "a" * 1001
    with pytest.raises(ValueError, match="Instruction exceeds maximum length"):
        interactive_engine.refine_node("s1", long_instruction)


def test_get_node_proxy(
    interactive_engine: InteractiveRaptorEngine, mock_store: MagicMock
) -> None:
    """Verify get_node proxies to store correctly."""
    interactive_engine.get_node("123")
    mock_store.get_node.assert_called_with("123")


def test_refine_node_unknown_dikw(
    interactive_engine: InteractiveRaptorEngine,
    mock_store: MagicMock,
    mock_summarizer: MagicMock
) -> None:
    """Test refinement with node having data level (no specific strategy)."""
    node = SummaryNode(
        id="s1",
        text="Summary",
        level=1,
        children_indices=[1],
        metadata=NodeMetadata(dikw_level=DIKWLevel.DATA) # Default level, might not be in registry
    )
    mock_store.get_node.return_value = node
    mock_store.get_nodes.return_value = iter([Chunk(index=1, text="C", start_char_idx=0, end_char_idx=1)])
    mock_store.transaction.return_value.__enter__.return_value = MagicMock()

    # Should work and use default strategy inside RefinementStrategy
    interactive_engine.refine_node("s1", "Refine")

    # Verify summarization called
    mock_summarizer.summarize.assert_called_once()


def test_refine_node_update_failure(
    interactive_engine: InteractiveRaptorEngine,
    mock_store: MagicMock,
    mock_summarizer: MagicMock
) -> None:
    """Test behavior when store update fails."""
    node = SummaryNode(
        id="s1",
        text="Summary",
        level=1,
        children_indices=[1],
        metadata=NodeMetadata()
    )
    mock_store.get_node.return_value = node
    mock_store.get_nodes.return_value = iter([Chunk(index=1, text="C", start_char_idx=0, end_char_idx=1)])

    # Simulate DB failure on update
    mock_store.update_node.side_effect = RuntimeError("DB Write Failed")

    with pytest.raises(RuntimeError, match="DB Write Failed"):
        interactive_engine.refine_node("s1", "Refine")

    # Verify update attempted
    mock_store.update_node.assert_called_once()
