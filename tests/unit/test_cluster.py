from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from domain_models.config import ProcessingConfig
from matome.engines.cluster import GMMClusterer


@pytest.fixture
def sample_embeddings() -> list[list[float]]:
    # 6 embeddings with 2 groups (to pass > 5 threshold)
    # Group 1: indices 0, 1, 2
    # Group 2: indices 3, 4, 5
    return [
        [1.0, 1.0], [1.0, 1.0], [1.0, 1.0],
        [2.0, 2.0], [2.0, 2.0], [2.0, 2.0]
    ]

@patch("matome.engines.cluster.UMAP")
@patch("matome.engines.cluster.GaussianMixture")
def test_clustering_with_gmm(mock_gmm_cls: MagicMock, mock_umap_cls: MagicMock, sample_embeddings: list[list[float]]) -> None:
    # Setup mocks
    mock_umap_instance = MagicMock()
    mock_umap_cls.return_value = mock_umap_instance
    # Reduce to 2 dimensions for GMM
    reduced_embeddings = np.array([
        [0.1, 0.1], [0.1, 0.1], [0.1, 0.1],
        [0.9, 0.9], [0.9, 0.9], [0.9, 0.9]
    ])
    mock_umap_instance.fit_transform.return_value = reduced_embeddings

    mock_gmm_instance = MagicMock()
    mock_gmm_cls.return_value = mock_gmm_instance
    # Predict returns cluster labels: [0, 0, 0, 1, 1, 1]
    mock_gmm_instance.predict.return_value = np.array([0, 0, 0, 1, 1, 1])
    # n_components_ is needed if we use it, but predict is key
    mock_gmm_instance.n_components = 2
    # Mock BIC scores: lowest for n=2 (first call)
    mock_gmm_instance.bic.side_effect = [10.0, 20.0, 30.0, 40.0, 50.0]

    # Instantiate engine
    engine = GMMClusterer()
    config = ProcessingConfig(clustering_algorithm="gmm")

    # Perform clustering
    clusters = engine.cluster_nodes(sample_embeddings, config)

    # We expect 2 clusters
    assert len(clusters) == 2

    # Check cluster 0
    c0 = next(c for c in clusters if c.id == 0)
    assert set(c0.node_indices) == {0, 1, 2}

    # Check cluster 1
    c1 = next(c for c in clusters if c.id == 1)
    assert set(c1.node_indices) == {3, 4, 5}

    # Verify calls
    mock_umap_cls.assert_called_once()
    mock_gmm_cls.assert_called() # Could be called multiple times for BIC search
    mock_umap_instance.fit_transform.assert_called()

def test_empty_embeddings() -> None:
    engine = GMMClusterer()
    config = ProcessingConfig()
    assert engine.cluster_nodes([], config) == []

@patch("matome.engines.cluster.UMAP")
@patch("matome.engines.cluster.GaussianMixture")
def test_fixed_n_clusters(mock_gmm_cls: MagicMock, mock_umap_cls: MagicMock, sample_embeddings: list[list[float]]) -> None:
    # Setup mocks
    mock_umap_instance = MagicMock()
    mock_umap_cls.return_value = mock_umap_instance
    mock_umap_instance.fit_transform.return_value = np.array(sample_embeddings)

    mock_gmm_instance = MagicMock()
    mock_gmm_cls.return_value = mock_gmm_instance
    mock_gmm_instance.predict.return_value = np.zeros(len(sample_embeddings))

    # Config with fixed clusters
    config = ProcessingConfig(n_clusters=3)
    engine = GMMClusterer()

    engine.cluster_nodes(sample_embeddings, config)

    # Should create GMM with n_components=3
    mock_gmm_cls.assert_called_with(n_components=3, random_state=42)

def test_single_cluster_forced(sample_embeddings: list[list[float]]) -> None:
    # Test that we handle n_clusters=1 gracefully if needed
    # Note: Even with n_clusters=1, if data > 5, it should go through UMAP/GMM flow,
    # unless GMM handles n=1 specially? GMM works with n=1.

    config = ProcessingConfig(n_clusters=1)
    engine = GMMClusterer()

    with patch("matome.engines.cluster.UMAP") as mock_umap, \
         patch("matome.engines.cluster.GaussianMixture") as mock_gmm:

        mock_umap.return_value.fit_transform.return_value = np.array(sample_embeddings)
        mock_gmm.return_value.predict.return_value = np.zeros(len(sample_embeddings))

        clusters = engine.cluster_nodes(sample_embeddings, config)

        assert len(clusters) == 1
        assert clusters[0].id == 0
        assert len(clusters[0].node_indices) == 6

        # Verify GMM called with 1 component
        mock_gmm.assert_called_with(n_components=1, random_state=42)

def test_very_small_dataset_skip(sample_embeddings: list[list[float]]) -> None:
    # Test skipping UMAP/GMM for <= 5 samples
    # Test with 5 samples
    small_embeddings = sample_embeddings[:5]

    config = ProcessingConfig()
    engine = GMMClusterer()

    with patch("matome.engines.cluster.UMAP") as mock_umap, \
         patch("matome.engines.cluster.GaussianMixture") as mock_gmm:

         clusters = engine.cluster_nodes(small_embeddings, config)

         assert len(clusters) == 1
         assert clusters[0].id == 0
         assert len(clusters[0].node_indices) == 5

         # Verify engines NOT called
         mock_umap.assert_not_called()
         mock_gmm.assert_not_called()
