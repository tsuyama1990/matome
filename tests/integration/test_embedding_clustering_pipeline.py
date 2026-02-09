"""
Integration test for Embedding and Clustering pipeline.
Mocks external dependencies to avoid network calls and heavy model loading.
"""

from typing import Any
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from domain_models.config import ProcessingConfig
from matome.engines.cluster import GMMClusterer
from matome.engines.embedder import EmbeddingService


@pytest.fixture
def mock_embeddings() -> list[list[float]]:
    # Create 3 clusters of points
    np.random.seed(42)
    c1 = np.random.normal(loc=[0, 0], scale=0.1, size=(10, 2))
    c2 = np.random.normal(loc=[5, 5], scale=0.1, size=(10, 2))
    c3 = np.random.normal(loc=[10, 0], scale=0.1, size=(10, 2))

    # Combine and shuffle
    data = np.vstack([c1, c2, c3])
    # Explicitly cast to list[list[float]]
    return [[float(x) for x in row] for row in data]

@pytest.fixture
def sample_chunks() -> list[str]:
    return [f"Chunk {i}" for i in range(30)]

def test_embedding_clustering_pipeline(mock_embeddings: list[list[float]], sample_chunks: list[str]) -> None:
    """Test the pipeline flow with mocked embeddings."""
    config = ProcessingConfig(
        embedding_model="mock-model",
        n_clusters=3,
        random_state=42
    )

    # Mock SentenceTransformer
    with patch("matome.engines.embedder.SentenceTransformer") as MockST:
        mock_instance = MagicMock()
        MockST.return_value = mock_instance

        # Configure encode to return our mock embeddings
        config = ProcessingConfig(
             embedding_model="mock-model",
             n_clusters=3,
             random_state=42,
             embedding_batch_size=100
        )

        def side_effect(texts: Any, **kwargs: Any) -> np.ndarray:
            # Return random embeddings matching the number of texts
            return np.array(mock_embeddings[:len(texts)])

        mock_instance.encode.side_effect = side_effect

        # 1. Embedding
        embedder = EmbeddingService(config)
        from domain_models.manifest import Chunk
        chunk_objects = [Chunk(index=i, text=t, start_char_idx=0, end_char_idx=10) for i, t in enumerate(sample_chunks)]

        # embed_chunks returns Iterator[Chunk], so we consume it
        embedded_chunks = list(embedder.embed_chunks(chunk_objects))

        assert len(embedded_chunks) == 30
        assert embedded_chunks[0].embedding is not None

        # 2. Clustering
        clusterer = GMMClusterer()
        # Extract embeddings and ensure they are not None
        valid_embeddings: list[list[float]] = []
        for c in embedded_chunks:
            if c.embedding is None:
                 pytest.fail("Embedding should not be None")
            valid_embeddings.append(c.embedding)

        clusters = clusterer.cluster_nodes(valid_embeddings, config)

        assert len(clusters) > 0
        # Check that we have valid clusters
        for cluster in clusters:
             assert cluster.node_indices

def test_real_pipeline_small() -> None:
    """
    Test using mocked SentenceTransformer but real UMAP/GMM.
    """
    config = ProcessingConfig(
        embedding_model="mock-model",
        n_clusters=2,
        random_state=42,
        umap_n_neighbors=5 # Small neighbors for small dataset
    )

    # Generate 10 random chunks
    texts = [f"Text {i}" for i in range(10)]

    with patch("matome.engines.embedder.SentenceTransformer") as MockST:
        mock_instance = MagicMock()
        MockST.return_value = mock_instance
        # Return 10 random vectors of dim 10
        mock_instance.encode.return_value = np.random.rand(10, 10)

        embedder = EmbeddingService(config)
        embeddings_gen = embedder.embed_strings(texts)
        embeddings = list(embeddings_gen)

        assert len(embeddings) == 10

        clusterer = GMMClusterer()
        clusters = clusterer.cluster_nodes(embeddings, config)

        assert len(clusters) > 0
        assert isinstance(clusters, list)
