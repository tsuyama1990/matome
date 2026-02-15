from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from domain_models.config import ProcessingConfig
from domain_models.types import NodeID
from matome.engines.cluster import GMMClusterer


@pytest.fixture
def sample_embeddings() -> list[tuple[NodeID, list[float]]]:
    # 6 embeddings with 2 groups
    # Group 1: indices 0, 1, 2
    # Group 2: indices 3, 4, 5
    return [
        (0, [1.0, 1.0]), (1, [1.0, 1.0]), (2, [1.0, 1.0]),
        (3, [2.0, 2.0]), (4, [2.0, 2.0]), (5, [2.0, 2.0])
    ]


@patch("matome.engines.cluster.MiniBatchKMeans")
@patch("matome.engines.cluster.IncrementalPCA")
def test_clustering_workflow(
    mock_pca_cls: MagicMock, mock_kmeans_cls: MagicMock, sample_embeddings: list[tuple[NodeID, list[float]]]
) -> None:
    # Setup mocks
    mock_pca_instance = MagicMock()
    mock_pca_cls.return_value = mock_pca_instance
    # transform returns array of shape (batch_size, n_components)
    mock_pca_instance.transform.side_effect = lambda x: x # Identity for test

    mock_kmeans_instance = MagicMock()
    mock_kmeans_cls.return_value = mock_kmeans_instance

    # Predict labels: 0 for first 3, 1 for next 3
    # Note: loop runs 3 times (partial_fit PCA, partial_fit KMeans, predict KMeans)
    # The predict loop iterates in batches.
    # If batch size is default 1000, it processes all 6 at once.
    mock_kmeans_instance.predict.return_value = np.array([0, 0, 0, 1, 1, 1])

    engine = GMMClusterer()
    config = ProcessingConfig(write_batch_size=100, umap_n_components=2)

    # Perform clustering
    clusters = engine.cluster_nodes(iter(sample_embeddings), config)

    # We expect 2 clusters
    assert len(clusters) == 2

    # Check cluster 0
    c0 = next(c for c in clusters if c.id == 0)
    assert set(c0.node_indices) == {"0", "1", "2"}

    # Check cluster 1
    c1 = next(c for c in clusters if c.id == 1)
    assert set(c1.node_indices) == {"3", "4", "5"}

    # Verify calls
    mock_pca_cls.assert_called()
    mock_kmeans_cls.assert_called()
    mock_pca_instance.partial_fit.assert_called()
    mock_kmeans_instance.partial_fit.assert_called()
    mock_kmeans_instance.predict.assert_called()


def test_empty_embeddings() -> None:
    engine = GMMClusterer()
    config = ProcessingConfig()
    assert engine.cluster_nodes([], config) == []


def test_very_small_dataset_skip(sample_embeddings: list[tuple[NodeID, list[float]]]) -> None:
    # Test skipping PCA/KMeans for <= 5 samples
    # Test with 5 samples
    small_embeddings = sample_embeddings[:5]

    config = ProcessingConfig()
    engine = GMMClusterer()

    with (
        patch("matome.engines.cluster.IncrementalPCA") as mock_pca,
        patch("matome.engines.cluster.MiniBatchKMeans") as mock_kmeans,
    ):
        # Pass as iterable
        clusters = engine.cluster_nodes(iter(small_embeddings), config)

        assert len(clusters) == 1
        assert clusters[0].id == 0
        # All 5 nodes in one cluster
        assert len(clusters[0].node_indices) == 5

        # Verify engines NOT called
        mock_pca.assert_not_called()
        mock_kmeans.assert_not_called()


@patch("matome.engines.cluster.MiniBatchKMeans")
@patch("matome.engines.cluster.IncrementalPCA")
def test_config_params(
    mock_pca_cls: MagicMock, mock_kmeans_cls: MagicMock, sample_embeddings: list[tuple[NodeID, list[float]]]
) -> None:
    """Test that algorithms are initialized with config parameters."""
    mock_pca_instance = MagicMock()
    mock_pca_cls.return_value = mock_pca_instance
    mock_pca_instance.transform.side_effect = lambda x: x

    mock_kmeans_instance = MagicMock()
    mock_kmeans_cls.return_value = mock_kmeans_instance
    mock_kmeans_instance.predict.return_value = np.zeros(len(sample_embeddings))

    config = ProcessingConfig(umap_n_components=5, random_state=123, n_clusters=2)
    engine = GMMClusterer()
    engine.cluster_nodes(sample_embeddings, config)

    # Check PCA call (umap_n_components maps to n_components in new implementation)
    pca_kwargs = mock_pca_cls.call_args.kwargs
    assert pca_kwargs["n_components"] == 5

    # Check KMeans call
    kmeans_kwargs = mock_kmeans_cls.call_args.kwargs
    assert kmeans_kwargs["random_state"] == 123
    assert kmeans_kwargs["n_clusters"] == 2
