import numpy as np
import pytest
from unittest.mock import MagicMock, patch

from domain_models.config import ProcessingConfig
from matome.engines.token_chunker import JapaneseTokenChunker
from matome.engines.cluster import GMMClusterer
from matome.engines.embedder import EmbeddingService
from matome.agents.summarizer import SummarizationAgent
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
    # Patch to avoid API key check
    with patch("matome.agents.summarizer.get_openrouter_api_key", return_value="mock"):
        summarizer = SummarizationAgent()
        assert isinstance(summarizer, Summarizer)

def test_configuration_flow() -> None:
    """Verify configuration object validation and default values."""
    # Test config inheritance and defaults
    config = ProcessingConfig(max_tokens=500)
    assert config.max_tokens == 500
    assert config.overlap == 0  # Default value
    assert config.clustering_algorithm == "gmm"  # Default

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
        umap_min_dist=0.0 # Default
    )

    chunker = JapaneseTokenChunker()
    clusterer = GMMClusterer()

    # Mock EmbeddingService to return deterministic embeddings
    with patch("matome.engines.embedder.SentenceTransformer") as mock_st_cls:
        mock_model = MagicMock()
        mock_st_cls.return_value = mock_model

        # Mock encode to return dummy vectors of size 10
        # The service calls encode with convert_to_numpy=True
        # We need to simulate that behavior
        def side_effect(texts, **kwargs):
             # Return random vectors for each text
             return np.random.rand(len(texts), 10)

        mock_model.encode.side_effect = side_effect

        embedder = EmbeddingService(config)

        # Mock SummarizationAgent
        # Use a fake key that is NOT 'mock' so we enter the real logic path
        # Also patch ChatOpenAI so we don't try to connect
        with patch("matome.agents.summarizer.get_openrouter_api_key", return_value="sk-fake-key"):
            with patch("matome.agents.summarizer.ChatOpenAI") as MockChatOpenAI:
                # Setup the mock instance
                mock_llm_instance = MagicMock()
                MockChatOpenAI.return_value = mock_llm_instance

                # Mock invoke response
                mock_response = MagicMock()
                mock_response.content = "Summary of the cluster."
                mock_llm_instance.invoke.return_value = mock_response

                summarizer = SummarizationAgent()

                # Act

                # 1. Chunking
                chunks = chunker.split_text(text, config)
                assert len(chunks) > 1, "Should have produced multiple chunks"

                # 2. Embedding
                chunks = embedder.embed_chunks(chunks)
                assert all(c.embedding is not None for c in chunks)
                assert all(len(c.embedding) == 10 for c in chunks) # Verify dimension

                # 3. Clustering
                # Clusterer expects embeddings list[list[float]]
                embeddings = [c.embedding for c in chunks]

                clusters = clusterer.cluster_nodes(embeddings, config)

                # Since we have random embeddings and small data, clustering might return 1 or more clusters.
                # We just verify the contract: returns List[Cluster]
                assert isinstance(clusters, list)
                assert len(clusters) > 0

                # 4. Summarization
                # Pick the first cluster and summarize its chunks
                cluster = clusters[0]
                cluster_text = " ".join([
                    # Find chunk text by index.
                    # Cluster.node_indices contains indices relative to the input list.
                    chunks[idx].text
                    for idx in cluster.node_indices
                ])

                summary = summarizer.summarize(cluster_text, config)

                # Assert
                assert summary == "Summary of the cluster."
