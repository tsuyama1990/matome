from collections.abc import Iterator

from domain_models.config import ClusteringAlgorithm, ProcessingConfig
from matome.engines.cluster import GMMClusterer


def test_cluster_edge_cases_empty_input() -> None:
    clusterer = GMMClusterer()
    config = ProcessingConfig(clustering_algorithm=ClusteringAlgorithm.GMM)

    # Empty input
    clusters = clusterer.cluster_nodes([], config) # type: ignore[arg-type]
    assert clusters == []

def test_cluster_edge_cases_single_point() -> None:
    clusterer = GMMClusterer()
    config = ProcessingConfig(clustering_algorithm=ClusteringAlgorithm.GMM)

    embeddings = [[0.1, 0.2]]

    def gen() -> Iterator[list[float]]:
        yield from embeddings

    clusters = clusterer.cluster_nodes(gen(), config)

    # Should return single cluster
    assert len(clusters) == 1
    assert len(clusters[0].node_indices) == 1
    assert clusters[0].node_indices[0] == 0

def test_cluster_edge_cases_small_dataset() -> None:
    # 3 points -> too small for UMAP usually, should fallback to 1 cluster
    clusterer = GMMClusterer()
    config = ProcessingConfig(clustering_algorithm=ClusteringAlgorithm.GMM)

    embeddings = [[0.1, 0.1], [0.2, 0.2], [0.3, 0.3]]

    def gen() -> Iterator[list[float]]:
        yield from embeddings

    clusters = clusterer.cluster_nodes(gen(), config)

    assert len(clusters) == 1
    assert len(clusters[0].node_indices) == 3
