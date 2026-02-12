import uuid
from collections.abc import Generator
from unittest.mock import MagicMock

import pytest

from domain_models.config import ProcessingConfig
from domain_models.manifest import Chunk, SummaryNode
from matome.agents.strategies import RefinementStrategy
from matome.engines.embedder import EmbeddingService
from matome.engines.interactive_raptor import InteractiveRaptorEngine
from matome.interfaces import Summarizer
from matome.utils.store import DiskChunkStore


@pytest.fixture
def mock_summarizer() -> MagicMock:
    summarizer = MagicMock(spec=Summarizer)
    summarizer.summarize.return_value = "Refined Summary"
    return summarizer


@pytest.fixture
def mock_embedder() -> MagicMock:
    embedder = MagicMock(spec=EmbeddingService)
    # embed_strings returns an iterator
    embedder.embed_strings.return_value = iter([[0.1, 0.2, 0.3]])
    return embedder


@pytest.fixture
def store() -> Generator[DiskChunkStore, None, None]:
    # Use in-memory DB for speed (default if no path provided is temp file)
    # But DiskChunkStore constructor creates a temp file if None.
    # To be truly in-memory, we might need specific sqlite url, but temp file is fine.
    store = DiskChunkStore()
    yield store
    store.close()


def test_refine_node_success(
    mock_summarizer: MagicMock, mock_embedder: MagicMock, store: DiskChunkStore
) -> None:
    config = ProcessingConfig()
    engine = InteractiveRaptorEngine(mock_summarizer, mock_embedder, config)

    # Setup initial node
    node_id = str(uuid.uuid4())
    initial_node = SummaryNode(
        id=node_id,
        text="Original Summary",
        level=1,
        children_indices=[],
        embedding=[0.0, 0.0, 0.0],
    )
    store.add_summary(initial_node)

    instruction = "Make it better"
    updated_node = engine.refine_node(node_id, instruction, store)

    # Verify summarizer called with correct args
    mock_summarizer.summarize.assert_called_once()
    call_args = mock_summarizer.summarize.call_args
    assert call_args.kwargs["text"] == "Original Summary"
    assert call_args.kwargs["context"] == {"instruction": instruction}
    # Check strategy type
    assert isinstance(call_args.kwargs["strategy"], RefinementStrategy)

    # Verify node updated
    assert updated_node.text == "Refined Summary"
    assert updated_node.metadata.is_user_edited is True
    assert instruction in updated_node.metadata.refinement_history
    assert updated_node.embedding == [0.1, 0.2, 0.3]

    # Verify store updated
    stored_node = store.get_node(node_id)
    assert stored_node is not None  # Type check for None
    assert stored_node.text == "Refined Summary"
    assert stored_node.embedding == [0.1, 0.2, 0.3]


def test_refine_node_not_found(
    mock_summarizer: MagicMock, mock_embedder: MagicMock, store: DiskChunkStore
) -> None:
    config = ProcessingConfig()
    engine = InteractiveRaptorEngine(mock_summarizer, mock_embedder, config)

    with pytest.raises(ValueError, match="not found"):
        engine.refine_node("non-existent-id", "instruction", store)


def test_refine_node_chunk_error(
    mock_summarizer: MagicMock, mock_embedder: MagicMock, store: DiskChunkStore
) -> None:
    config = ProcessingConfig()
    engine = InteractiveRaptorEngine(mock_summarizer, mock_embedder, config)

    # Add a chunk (not summary node)
    chunk = Chunk(index=0, text="Raw chunk", start_char_idx=0, end_char_idx=9)
    store.add_chunk(chunk)

    with pytest.raises(TypeError, match="Cannot refine raw data chunks"):
        engine.refine_node("0", "instruction", store)
