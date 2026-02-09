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
    return [[1.0, 1.0], [1.0, 1.0], [1.0, 1.0], [2.0, 2.0], [2.0, 2.0], [2.0, 2.0]]


@patch("matome.engines.cluster.UMAP")
@patch("matome.engines.cluster.GaussianMixture")
def test_clustering_with_gmm_soft(
    mock_gmm_cls: MagicMock, mock_umap_cls: MagicMock, sample_embeddings: list[list[float]]
) -> None:
    # Setup mocks
    mock_umap_instance = MagicMock()
    mock_umap_cls.return_value = mock_umap_instance
    reduced_embeddings = np.array(
        [[0.1, 0.1], [0.1, 0.1], [0.1, 0.1], [0.9, 0.9], [0.9, 0.9], [0.9, 0.9]]
    )
    mock_umap_instance.fit_transform.return_value = reduced_embeddings

    mock_gmm_instance = MagicMock()
    mock_gmm_cls.return_value = mock_gmm_instance

    # Soft Clustering Probabilities (N=6, K=2)
    # 0,1,2 -> Cluster 0 (Prob ~0.9, 0.1)
    # 3,4,5 -> Cluster 1 (Prob ~0.1, 0.9)
    # Node 2 is ambiguous -> (Prob 0.45, 0.55). Max is 1, but if threshold is 0.4, both selected.
    # Let's test that logic.
    probs = np.array([
        [0.9, 0.1],
        [0.9, 0.1],
        [0.45, 0.55], # Ambiguous
        [0.1, 0.9],
        [0.1, 0.9],
        [0.1, 0.9]
    ])
    mock_gmm_instance.predict_proba.return_value = probs

    # Mock BIC scores to select 2 clusters
    mock_gmm_instance.bic.side_effect = [10.0, 20.0, 30.0, 40.0, 50.0]

    # Instantiate engine with threshold 0.4
    engine = GMMClusterer()
    config = ProcessingConfig(clustering_algorithm="gmm", clustering_probability_threshold=0.4)

    # Perform clustering
    clusters = engine.cluster_nodes(iter(sample_embeddings), config)

    # We expect 2 clusters
    assert len(clusters) == 2

    # Check cluster 0
    c0 = next(c for c in clusters if c.id == 0)
    # Node 2 (0.45) >= 0.4, so it should be in C0
    assert set(c0.node_indices) == {0, 1, 2}

    # Check cluster 1
    c1 = next(c for c in clusters if c.id == 1)
    # Node 2 (0.55) >= 0.4, so it should be in C1 too
    assert set(c1.node_indices) == {2, 3, 4, 5}

    # Verify calls
    mock_umap_cls.assert_called_once()
    mock_gmm_instance.predict_proba.assert_called()


def test_empty_embeddings() -> None:
    engine = GMMClusterer()
    config = ProcessingConfig()
    assert engine.cluster_nodes([], config) == []


@patch("matome.engines.cluster.UMAP")
@patch("matome.engines.cluster.GaussianMixture")
def test_fixed_n_clusters(
    mock_gmm_cls: MagicMock, mock_umap_cls: MagicMock, sample_embeddings: list[list[float]]
) -> None:
    # Setup mocks
    mock_umap_instance = MagicMock()
    mock_umap_cls.return_value = mock_umap_instance
    mock_umap_instance.fit_transform.return_value = np.array(sample_embeddings)

    mock_gmm_instance = MagicMock()
    mock_gmm_cls.return_value = mock_gmm_instance
    # Needs predict_proba
    mock_gmm_instance.predict_proba.return_value = np.zeros((len(sample_embeddings), 3))

    # Config with fixed clusters
    config = ProcessingConfig(n_clusters=3)
    engine = GMMClusterer()

    engine.cluster_nodes(sample_embeddings, config)

    # Should create GMM with n_components=3
    mock_gmm_cls.assert_called_with(n_components=3, random_state=42)


def test_very_small_dataset_skip(sample_embeddings: list[list[float]]) -> None:
    # Test skipping UMAP/GMM for <= 5 samples
    # Test with 5 samples
    small_embeddings = sample_embeddings[:5]

    config = ProcessingConfig()
    engine = GMMClusterer()

    with (
        patch("matome.engines.cluster.UMAP") as mock_umap,
        patch("matome.engines.cluster.GaussianMixture") as mock_gmm,
    ):
        # Pass as iterable
        clusters = engine.cluster_nodes(iter(small_embeddings), config)

        assert len(clusters) == 1
        assert clusters[0].id == 0
        assert len(clusters[0].node_indices) == 5

        # Verify engines NOT called
        mock_umap.assert_not_called()
        mock_gmm.assert_not_called()


@patch("matome.engines.cluster.UMAP")
@patch("matome.engines.cluster.GaussianMixture")
def test_umap_config_params(
    mock_gmm_cls: MagicMock, mock_umap_cls: MagicMock, sample_embeddings: list[list[float]]
) -> None:
    """Test that UMAP is initialized with config parameters."""
    mock_umap_instance = MagicMock()
    mock_umap_cls.return_value = mock_umap_instance
    mock_umap_instance.fit_transform.return_value = np.array(sample_embeddings)
    mock_gmm_cls.return_value.predict_proba.return_value = np.zeros((len(sample_embeddings), 3))

    config = ProcessingConfig(umap_n_components=3, umap_n_neighbors=5, umap_min_dist=0.0)
    engine = GMMClusterer()
    engine.cluster_nodes(sample_embeddings, config)

    # Check UMAP call
    call_kwargs = mock_umap_cls.call_args.kwargs
    assert call_kwargs["n_components"] == 3
    assert call_kwargs["n_neighbors"] == 5
    assert call_kwargs["min_dist"] == 0.0
