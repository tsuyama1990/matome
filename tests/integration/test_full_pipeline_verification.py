from collections.abc import Iterable
from typing import Any
from unittest.mock import MagicMock, patch

import numpy as np

from domain_models.config import ProcessingConfig
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
    summarizer = SummarizationAgent(config, llm=mock_llm)
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
    text = "これはテストです。文書を分割し、クラスタリングし、要約します。" * 5  # Make it long enough for multiple chunks
    config = ProcessingConfig(
        max_tokens=20,  # Small token limit to force multiple chunks
        umap_n_neighbors=2, # Small neighbors for small dataset
        umap_min_dist=0.0, # Default
        write_batch_size=5 # Small batch size for testing streaming
    )

    chunker = JapaneseTokenChunker()
    clusterer = GMMClusterer()

    # Mock EmbeddingService to return deterministic embeddings
    with patch("matome.engines.embedder.SentenceTransformer") as mock_st_cls:
        mock_model = MagicMock()
        mock_st_cls.return_value = mock_model

        # Mock encode to return deterministic vectors
        # Using a fixed RNG to ensure determinism across test runs
        # Patching np.random.default_rng is hard, so we use a deterministic side_effect

        def side_effect(texts: Iterable[str], **kwargs: Any) -> np.ndarray:
             text_list = list(texts)
             # Use a fixed seed for every call to ensure consistent output
             rng = np.random.default_rng(42)
             # We want different vectors for different calls but deterministic overall?
             # Simple deterministic generation:
             count = len(text_list)
             # Generate based on index or just random with fixed seed
             return rng.random((count, 10))

        mock_model.encode.side_effect = side_effect

        embedder = EmbeddingService(config)

        # Mock LLM for SummarizationAgent
        mock_llm_instance = MagicMock()
        mock_response = MagicMock()
        mock_response.content = "Summary of the cluster."
        mock_llm_instance.invoke.return_value = mock_response

        # Use dependency injection
        summarizer = SummarizationAgent(config, llm=mock_llm_instance)

        # Act & Assert (Logic same as before, but with deterministic RNG)
        chunks = chunker.split_text(text, config)
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
        summary = summarizer.summarize(cluster_text, config)
        assert summary == "Summary of the cluster."
