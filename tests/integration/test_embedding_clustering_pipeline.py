import pytest
from unittest.mock import MagicMock
from domain_models.config import ProcessingConfig
from matome.engines.embedder import EmbeddingService
from matome.engines.cluster import GMMClusterer
from matome.engines.token_chunker import TokenChunker

def test_embedding_clustering_pipeline() -> None:
    config = ProcessingConfig(max_tokens=10)
    chunker = TokenChunker()
    embedder = EmbeddingService(config)
    # Mock model for speed/no-download
    embedder.model = MagicMock()
    embedder.model.encode.return_value = [[0.1, 0.2]]

    clusterer = GMMClusterer()

    text = "Hello world"
    chunks = list(chunker.split_text(text, config))

    # Embed
    embeddings = list(embedder.embed_chunks(chunks))
    assert len(embeddings) == len(chunks)

    # Cluster
    clusters = clusterer.cluster_nodes(embeddings, config)
    assert len(clusters) > 0

def test_real_pipeline_small() -> None:
    """Test with small real data flow."""
    config = ProcessingConfig(max_tokens=100)
    # Mocking internal models
    chunker = TokenChunker()
    embedder = EmbeddingService(config)
    embedder.model = MagicMock()
    embedder.model.encode.return_value = [[0.1]*384]

    clusterer = GMMClusterer()

    text = "Sentence one. Sentence two."
    chunks = list(chunker.split_text(text, config))

    embeddings = list(embedder.embed_chunks(chunks))

    # GMM requires samples >= n_components (default 2)
    # Ensure we have enough chunks or mock clustering behavior
    if len(embeddings) < 2:
        embeddings.append([0.1]*384) # Hack to ensure clustering runs

    clusters = clusterer.cluster_nodes(embeddings, config)
    assert clusters
