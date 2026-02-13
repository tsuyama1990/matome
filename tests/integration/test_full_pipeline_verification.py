from collections.abc import Iterable
from typing import Any
from unittest.mock import MagicMock, patch

import numpy as np

from domain_models.config import ProcessingConfig
from matome.agents.strategies import BaseSummaryStrategy
from matome.agents.summarizer import SummarizationAgent
from matome.engines.cluster import GMMClusterer
from matome.engines.embedder import EmbeddingService
from matome.engines.token_chunker import JapaneseTokenChunker
from matome.interfaces import Chunker, Clusterer, Summarizer


def test_interface_compliance() -> None:
    """Verify that all components strictly adhere to their interfaces."""
    # Chunker
    chunker = JapaneseTokenChunker()
    assert isinstance(chunker, Chunker)

    # Clusterer
    clusterer = GMMClusterer()
    assert isinstance(clusterer, Clusterer)

    # Summarizer
    # Use dependency injection to avoid API key requirement
    config = ProcessingConfig()
    mock_llm = MagicMock()
    summarizer = SummarizationAgent(config, strategy=BaseSummaryStrategy(), llm=mock_llm)
    assert isinstance(summarizer, Summarizer)


def test_configuration_flow() -> None:
    """Verify configuration object validation and default values."""
    # Test config inheritance and defaults
    config = ProcessingConfig(max_tokens=500)
    assert config.max_tokens == 500
    assert config.overlap == 0  # Default value
    assert config.clustering_algorithm.value == "gmm"  # Default


def test_full_pipeline_flow() -> None:
    """
    End-to-End verification of the data flow:
    Text -> Chunker -> EmbeddingService -> Clusterer -> Summarizer
    """
    # Arrange
    text = (
        "これはテストです。文書を分割し、クラスタリングし、要約します。" * 5
    )  # Make it long enough for multiple chunks
    config = ProcessingConfig(
        max_tokens=20,  # Small token limit to force multiple chunks
        umap_n_neighbors=2,  # Small neighbors for small dataset
        umap_min_dist=0.0,  # Default
        write_batch_size=5,  # Small batch size for testing streaming
    )

    chunker = JapaneseTokenChunker()
    clusterer = GMMClusterer()

    # Mock EmbeddingService to return deterministic embeddings
    with patch("matome.engines.embedder.SentenceTransformer") as mock_st_cls:
        mock_model = MagicMock()
        mock_st_cls.return_value = mock_model

        # Mock encode to return deterministic vectors
        # Using a fixed RNG to ensure determinism across test runs
        # We define the RNG outside the side_effect so it maintains state across calls
        rng = np.random.default_rng(42)

        def side_effect(texts: Iterable[str], **kwargs: Any) -> np.ndarray:
            text_list = list(texts)
            count = len(text_list)
            # Returns standard uniform [0.0, 1.0)
            return rng.random((count, 10))

        mock_model.encode.side_effect = side_effect

        embedder = EmbeddingService(config)

        # Mock LLM for SummarizationAgent
        mock_llm_instance = MagicMock()
        mock_response = MagicMock()
        mock_response.content = "Summary of the cluster."
        mock_llm_instance.invoke.return_value = mock_response

        # Use dependency injection
        summarizer = SummarizationAgent(
            config, strategy=BaseSummaryStrategy(), llm=mock_llm_instance
        )

        # Act & Assert (Logic same as before, but with deterministic RNG)
        chunks = list(chunker.split_text(text, config))
        assert len(chunks) > 1

        chunks_with_embeddings = list(embedder.embed_chunks(chunks))
        assert all(c.embedding is not None for c in chunks_with_embeddings)

        valid_embeddings: list[list[float]] = []
        for c in chunks_with_embeddings:
            assert c.embedding is not None, "Embedding should not be None"
            valid_embeddings.append(c.embedding)

        # Ensure we patch GMM/UMAP randomness if needed, but config.random_state handles it
        clusters = clusterer.cluster_nodes(valid_embeddings, config)
        assert isinstance(clusters, list)
        assert len(clusters) > 0

        cluster = clusters[0]
        cluster_text_parts = []
        for idx in cluster.node_indices:
            cluster_text_parts.append(chunks_with_embeddings[int(idx)].text)

        cluster_text = " ".join(cluster_text_parts)
        summary_node = summarizer.summarize(
            cluster_text, context={"id": "test", "level": 1, "children_indices": []}
        )
        assert summary_node.text == "Summary of the cluster."


def test_pipeline_streaming_logic() -> None:
    """
    Explicit test to verify that large datasets (simulated by small batch size)
    are processed correctly without errors, implying streaming logic works.
    """
    # Create a large enough list of dummy embeddings
    # 20 items, batch size 5 => 4 batches
    embeddings = [[0.1 * i] * 10 for i in range(20)]

    config = ProcessingConfig(write_batch_size=5, umap_n_neighbors=2, umap_n_components=2)

    clusterer = GMMClusterer()

    # We just want to ensure it runs without crashing and returns clusters
    # This exercises the _stream_write_embeddings loop
    clusters = clusterer.cluster_nodes(embeddings, config)

    assert len(clusters) > 0
    # Check total nodes clustered equals input
    total_nodes = sum(len(c.node_indices) for c in clusters)
    assert total_nodes == 20
