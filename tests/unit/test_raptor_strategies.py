from unittest.mock import create_autospec

import pytest

from unittest.mock import MagicMock

from domain_models.config import ProcessingConfig, ProcessingMode
from domain_models.manifest import Cluster
from matome.agents.strategies import (
    ActionStrategy,
    BaseSummaryStrategy,
    KnowledgeStrategy,
    WisdomStrategy,
)
from matome.engines.embedder import EmbeddingService
from matome.engines.raptor import RaptorEngine
from matome.interfaces import Chunker, Clusterer, Summarizer


@pytest.fixture
def mock_dependencies() -> tuple[Chunker, EmbeddingService, Clusterer, Summarizer]:
    return (
        create_autospec(Chunker, instance=True),
        create_autospec(EmbeddingService, instance=True),
        create_autospec(Clusterer, instance=True),
        create_autospec(Summarizer, instance=True),
    )


def test_strategy_selection_dikw(
    mock_dependencies: tuple[Chunker, EmbeddingService, Clusterer, Summarizer],
) -> None:
    """Verify DIKW strategy selection logic."""
    chunker, embedder, clusterer, summarizer = mock_dependencies
    config = ProcessingConfig(processing_mode=ProcessingMode.DIKW)
    engine = RaptorEngine(chunker, embedder, clusterer, summarizer, config)

    # Test Level 1 -> Action
    s, _ = engine._get_strategy_for_level(1)
    assert isinstance(s, ActionStrategy)

    # Test Level 2 -> Knowledge
    s, _ = engine._get_strategy_for_level(2)
    assert isinstance(s, KnowledgeStrategy)

    # Test Level 3 -> Wisdom
    s, _ = engine._get_strategy_for_level(3)
    assert isinstance(s, WisdomStrategy)


def test_strategy_selection_default(
    mock_dependencies: tuple[Chunker, EmbeddingService, Clusterer, Summarizer],
) -> None:
    """Verify Default strategy selection logic (preserves backward compatibility)."""
    chunker, embedder, clusterer, summarizer = mock_dependencies
    config = ProcessingConfig(processing_mode=ProcessingMode.DEFAULT)
    engine = RaptorEngine(chunker, embedder, clusterer, summarizer, config)

    # Test Level 1 -> Base
    s, _ = engine._get_strategy_for_level(1)
    assert isinstance(s, BaseSummaryStrategy)

    # Test Level 3 -> Base
    s, _ = engine._get_strategy_for_level(3)
    assert isinstance(s, BaseSummaryStrategy)


def test_summarize_clusters_integration(
    mock_dependencies: tuple[Chunker, EmbeddingService, Clusterer, Summarizer],
) -> None:
    """Verify _summarize_clusters calls summarizer with correct strategy."""
    chunker, embedder, clusterer, summarizer = mock_dependencies
    summarizer.summarize.return_value = "summary text"
    store = MagicMock()

    # Setup mock node
    store.get_node.return_value = MagicMock(text="content")
    cluster = Cluster(id="c1", level=0, node_indices=[0])

    # 1. DIKW Mode
    config_dikw = ProcessingConfig(processing_mode=ProcessingMode.DIKW)
    engine_dikw = RaptorEngine(chunker, embedder, clusterer, summarizer, config_dikw)

    # Consume generator
    list(engine_dikw._summarize_clusters([cluster], [0], store, level=1))

    # Check call
    _, kwargs = summarizer.summarize.call_args
    assert isinstance(kwargs['strategy'], ActionStrategy)

    # 2. Default Mode
    config_default = ProcessingConfig(processing_mode=ProcessingMode.DEFAULT)
    engine_default = RaptorEngine(chunker, embedder, clusterer, summarizer, config_default)

    list(engine_default._summarize_clusters([cluster], [0], store, level=1))

    _, kwargs = summarizer.summarize.call_args
    assert isinstance(kwargs['strategy'], BaseSummaryStrategy)
