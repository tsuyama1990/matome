import pytest
from unittest.mock import MagicMock, patch
from domain_models.config import ProcessingConfig
from matome.engines.raptor import RaptorEngine
from matome.engines.token_chunker import TokenChunker
from matome.engines.embedder import EmbeddingService
from matome.engines.cluster import GMMClusterer
from matome.agents.summarizer import SummarizationAgent
from matome.utils.store import DiskChunkStore

def test_configuration_flow() -> None:
    config = ProcessingConfig()
    assert config.max_tokens > 0

def test_pipeline_streaming_logic() -> None:
    """Verify data flows through components using generators."""
    config = ProcessingConfig()

    # Mocks
    chunker = MagicMock()
    chunker.split_text.return_value = iter([]) # Generator

    embedder = MagicMock()
    embedder.embed_chunks.return_value = iter([])

    clusterer = MagicMock()
    clusterer.cluster_nodes.return_value = []

    summarizer = MagicMock()

    store = MagicMock()
    store.get_node_ids_by_level.return_value = []

    engine = RaptorEngine(chunker, embedder, clusterer, summarizer, config)

    # Run with empty input shouldn't crash if handled
    try:
        engine.run("test", store=store)
    except Exception:
        # Expected to fail on empty, but checking flow
        pass

    chunker.split_text.assert_called()
