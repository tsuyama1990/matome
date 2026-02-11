from collections.abc import Iterator

import pytest

from domain_models.config import ClusteringAlgorithm, ProcessingConfig
from domain_models.manifest import Cluster
from matome.engines.cluster import GMMClusterer


@pytest.fixture
def mock_embeddings() -> list[list[float]]:
    # 10 samples, 2 dimensions
    return [
        [0.1, 0.1], [0.2, 0.2], [0.1, 0.2], [0.2, 0.1],  # Cluster A
        [0.9, 0.9], [0.8, 0.8], [0.9, 0.8], [0.8, 0.9],  # Cluster B
        [0.5, 0.5], [0.55, 0.55]                         # Noise / Small Cluster
    ]

@pytest.fixture
def config() -> ProcessingConfig:
    # Use Enum for clustering_algorithm
    return ProcessingConfig(
        n_clusters=2,
        clustering_algorithm=ClusteringAlgorithm.GMM,
        random_state=42
    )

def test_gmm_clusterer_initialization() -> None:
    clusterer = GMMClusterer()
    assert clusterer is not None

def test_cluster_nodes_basic(mock_embeddings: list[list[float]], config: ProcessingConfig) -> None:
    clusterer = GMMClusterer()

    # Mock generator
    def embedding_gen() -> Iterator[list[float]]:
        yield from mock_embeddings

    # Correct return type unpacking (it returns list[Cluster] only)
    clusters = clusterer.cluster_nodes(embedding_gen(), config)

    assert len(clusters) > 0
    # No node_ids returned, so we can't check length of node_ids.
    assert isinstance(clusters[0], Cluster)

    # Check that all nodes are assigned
    assigned_indices = set()
    for c in clusters:
        for idx in c.node_indices:
            assigned_indices.add(idx)

    assert len(assigned_indices) == len(mock_embeddings)

def test_cluster_nodes_soft_clustering(config: ProcessingConfig) -> None:
    # Scenario where a point is between two clusters
    embeddings = [
        [0.1, 0.1], [0.1, 0.11], # Cluster 1
        [0.9, 0.9], [0.9, 0.91], # Cluster 2
        [0.5, 0.5]               # Ambiguous
    ]

    clusterer = GMMClusterer()
    # Low threshold to allow multiple assignment
    config_soft = ProcessingConfig(
        clustering_probability_threshold=0.01,
        clustering_algorithm=ClusteringAlgorithm.GMM
    )

    def gen() -> Iterator[list[float]]:
        yield from embeddings

    clusters = clusterer.cluster_nodes(gen(), config_soft)

    # Just verify structure
    assert isinstance(clusters, list)
    assert all(isinstance(c, Cluster) for c in clusters)
