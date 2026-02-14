from unittest.mock import MagicMock, patch

import numpy as np

from domain_models.config import ProcessingConfig
from domain_models.manifest import Chunk
from matome.engines.cluster import GMMClusterer
from matome.engines.embedder import EmbeddingService
from domain_models.types import NodeID


# Scenario 05: Embedding Vector Generation
def test_scenario_05_embedding_vector_generation() -> None:
    chunks = [
        Chunk(index=0, text="This is a test.", start_char_idx=0, end_char_idx=15),
        Chunk(index=1, text="Another sentence.", start_char_idx=16, end_char_idx=33),
    ]

    with patch("matome.engines.embedder.SentenceTransformer") as mock_st:
        mock_instance = MagicMock()
        mock_st.return_value = mock_instance
        # Use fixed vectors instead of random
        # Vector dim 4 for simplicity
        fixed_vecs = [[0.1, 0.2, 0.3, 0.4], [0.5, 0.6, 0.7, 0.8]]
        mock_instance.encode.return_value = np.array(fixed_vecs)

        config = ProcessingConfig()
        service = EmbeddingService(config)
        embedded_chunks = list(service.embed_chunks(chunks))

        for i, chunk in enumerate(embedded_chunks):
            assert chunk.embedding is not None
            assert len(chunk.embedding) == 4
            assert chunk.embedding == fixed_vecs[i]


# Scenario 06: Clustering Logic Verification
def test_scenario_06_clustering_logic() -> None:
    # 3 Apple Pie (Cluster A), 3 Python (Cluster B)
    # Use deterministic vectors
    group_a = [[0.1] * 10, [0.11] * 10, [0.09] * 10]
    group_b = [[0.9] * 10, [0.91] * 10, [0.89] * 10]
    all_embeddings = group_a + group_b
    embeddings = [(str(i), emb) for i, emb in enumerate(all_embeddings)]

    config = ProcessingConfig(clustering_algorithm="gmm")
    engine = GMMClusterer()

    with (
        patch("matome.engines.cluster.IncrementalPCA") as mock_pca,
        patch("matome.engines.cluster.MiniBatchKMeans") as mock_kmeans,
    ):
        mock_pca_instance = MagicMock()
        mock_pca.return_value = mock_pca_instance
        mock_pca_instance.transform.side_effect = lambda x: x # Identity

        mock_kmeans_instance = MagicMock()
        mock_kmeans.return_value = mock_kmeans_instance

        # Determine labels: first 3 -> 0, next 3 -> 1
        mock_kmeans_instance.predict.return_value = np.array([0, 0, 0, 1, 1, 1])

        clusters = engine.cluster_nodes(embeddings, config)

        assert len(clusters) == 2

        # Verify grouping
        cluster_0 = next(c for c in clusters if c.id == 0)
        cluster_1 = next(c for c in clusters if c.id == 1)

        # Assuming cluster 0 and 1 are distinct
        # IDs are strings
        indices_set_0 = set(cluster_0.node_indices)
        indices_set_1 = set(cluster_1.node_indices)

        expected_sets = [{"0", "1", "2"}, {"3", "4", "5"}]
        assert indices_set_0 in expected_sets
        assert indices_set_1 in expected_sets
        assert indices_set_0 != indices_set_1


# Scenario 07: Single Cluster Edge Case
def test_scenario_07_single_cluster() -> None:
    embeddings = [(0, [0.5] * 10)]

    config = ProcessingConfig()
    engine = GMMClusterer()

    clusters = engine.cluster_nodes(embeddings, config)

    assert len(clusters) == 1
    assert clusters[0].id == 0
    # NodeID can be int or str, GMMClusterer returns what was passed or parsed from file
    # GMMClusterer writes to file then reads back as string usually?
    # Let's check implementation of _form_clusters. It reads lines from file.
    # So IDs will be strings.
    assert str(clusters[0].node_indices[0]) == "0"
