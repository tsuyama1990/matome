from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from domain_models.config import ProcessingConfig
from domain_models.manifest import Chunk
from matome.engines.cluster import ClusterEngine


@pytest.fixture
def sample_chunks() -> list[Chunk]:
    # Return 4 chunks
    return [
        Chunk(index=i, text=f"Chunk {i}", start_char_idx=0, end_char_idx=5)
        for i in range(4)
    ]

@pytest.fixture
def sample_embeddings() -> np.ndarray:
    # 4 embeddings with 2 groups
    # Group 1: indices 0, 1 (all ones)
    # Group 2: indices 2, 3 (all twos)
    return np.array([
        [1.0, 1.0], [1.0, 1.0],
        [2.0, 2.0], [2.0, 2.0]
    ])

@patch("matome.engines.cluster.UMAP")
@patch("matome.engines.cluster.GaussianMixture")
def test_clustering_with_gmm(mock_gmm_cls: MagicMock, mock_umap_cls: MagicMock, sample_chunks: list[Chunk], sample_embeddings: np.ndarray) -> None:
    # Setup mocks
    mock_umap_instance = MagicMock()
    mock_umap_cls.return_value = mock_umap_instance
    # Reduce to 2 dimensions for GMM
    reduced_embeddings = np.array([
        [0.1, 0.1], [0.1, 0.1],
        [0.9, 0.9], [0.9, 0.9]
    ])
    mock_umap_instance.fit_transform.return_value = reduced_embeddings

    mock_gmm_instance = MagicMock()
    mock_gmm_cls.return_value = mock_gmm_instance
    # Predict returns cluster labels: [0, 0, 1, 1]
    mock_gmm_instance.predict.return_value = np.array([0, 0, 1, 1])
    # n_components_ is needed if we use it, but predict is key
    mock_gmm_instance.n_components = 2
    # Mock BIC scores: lowest for n=2 (first call)
    mock_gmm_instance.bic.side_effect = [10.0, 20.0, 30.0, 40.0, 50.0]

    # Instantiate engine
    config = ProcessingConfig(clustering_algorithm="gmm")
    engine = ClusterEngine(config)

    # Perform clustering
    clusters = engine.perform_clustering(sample_chunks, sample_embeddings)

    # We expect 2 clusters
    assert len(clusters) == 2

    # Check cluster 0
    c0 = next(c for c in clusters if c.id == 0)
    assert set(c0.node_indices) == {0, 1}

    # Check cluster 1
    c1 = next(c for c in clusters if c.id == 1)
    assert set(c1.node_indices) == {2, 3}

    # Verify calls
    mock_umap_cls.assert_called_once()
    mock_gmm_cls.assert_called() # Could be called multiple times for BIC search
    mock_umap_instance.fit_transform.assert_called_with(sample_embeddings)

def test_empty_chunks(sample_chunks: list[Chunk]) -> None:
    config = ProcessingConfig()
    engine = ClusterEngine(config)
    assert engine.perform_clustering([], np.array([])) == []

@patch("matome.engines.cluster.UMAP")
@patch("matome.engines.cluster.GaussianMixture")
def test_fixed_n_clusters(mock_gmm_cls: MagicMock, mock_umap_cls: MagicMock, sample_chunks: list[Chunk], sample_embeddings: np.ndarray) -> None:
    # Setup mocks
    mock_umap_instance = MagicMock()
    mock_umap_cls.return_value = mock_umap_instance
    mock_umap_instance.fit_transform.return_value = sample_embeddings

    mock_gmm_instance = MagicMock()
    mock_gmm_cls.return_value = mock_gmm_instance
    mock_gmm_instance.predict.return_value = np.zeros(len(sample_chunks))

    # Config with fixed clusters
    config = ProcessingConfig(n_clusters=3)
    engine = ClusterEngine(config)

    engine.perform_clustering(sample_chunks, sample_embeddings)

    # Should create GMM with n_components=3
    mock_gmm_cls.assert_called_with(n_components=3, random_state=42)
