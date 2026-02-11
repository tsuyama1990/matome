from unittest.mock import MagicMock, patch

import numpy as np

from domain_models.config import ClusteringAlgorithm, ProcessingConfig
from domain_models.manifest import Chunk
from matome.engines.cluster import GMMClusterer
from matome.engines.embedder import EmbeddingService


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
        # Mock batched to ensure test doesn't fail if we switched to batched
        with patch("matome.engines.embedder.batched", side_effect=lambda x, y: [tuple(x)]):
             pass

        embedded_chunks = list(service.embed_chunks(chunks))

        for i, chunk in enumerate(embedded_chunks):
            assert chunk.embedding is not None
            assert chunk.embedding == fixed_vecs[i]


# Scenario 06: Clustering Logic Verification
def test_scenario_06_clustering_logic() -> None:
    # 3 Apple Pie (Cluster A), 3 Python (Cluster B)
    # Use deterministic vectors
    group_a = [[0.1] * 10] * 3
    group_b = [[0.9] * 10] * 3
    embeddings = group_a + group_b

    # Instantiate config with n_clusters=2 since it is frozen
    config = ProcessingConfig(
        clustering_algorithm=ClusteringAlgorithm.GMM,
        n_clusters=2
    )
    clusterer = GMMClusterer()

    with patch("matome.engines.cluster.GaussianMixture") as MockGMM:
        instance = MockGMM.return_value
        probs = np.zeros((6, 2))
        probs[:3, 0] = 0.99
        probs[:3, 1] = 0.01
        probs[3:, 0] = 0.01
        probs[3:, 1] = 0.99
        instance.predict_proba.return_value = probs

        clusters = clusterer.cluster_nodes(embeddings, config)

        assert len(clusters) == 2
        # Collect sets of indices
        sets = [set(c.node_indices) for c in clusters]

        # We expect {0,1,2} and {3,4,5}
        expected_1 = {0, 1, 2}
        expected_2 = {3, 4, 5}

        assert expected_1 in sets
        assert expected_2 in sets


# Scenario 07: Single Cluster Edge Case
def test_scenario_07_single_cluster() -> None:
    embeddings = [[0.5] * 10]

    config = ProcessingConfig()
    clusterer = GMMClusterer()

    clusters = clusterer.cluster_nodes(embeddings, config)

    assert len(clusters) == 1
    # ID is 0 for single cluster usually, but let's just check length and content
    assert len(clusters[0].node_indices) == 1
    assert clusters[0].node_indices == [0]
