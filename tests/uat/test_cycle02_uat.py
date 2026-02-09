from unittest.mock import MagicMock, patch

import numpy as np

from domain_models.config import ProcessingConfig
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
        # Use small vector dimension (32) to save memory in tests
        mock_instance.encode.return_value = np.array(
            [list(np.random.rand(32)), list(np.random.rand(32))]
        )

        config = ProcessingConfig()
        service = EmbeddingService(config)
        embedded_chunks = service.embed_chunks(chunks)

        for chunk in embedded_chunks:
            assert chunk.embedding is not None
            assert len(chunk.embedding) == 32


# Scenario 06: Clustering Logic Verification
def test_scenario_06_clustering_logic() -> None:
    # 3 Apple Pie, 3 Python
    # Use 10-dim vectors for simplicity
    group_a = [np.random.normal(0, 0.1, 10).tolist() for _ in range(3)]
    group_b = [np.random.normal(5, 0.1, 10).tolist() for _ in range(3)]
    embeddings = group_a + group_b

    config = ProcessingConfig(clustering_algorithm="gmm")
    engine = GMMClusterer()

    with (
        patch("matome.engines.cluster.UMAP") as mock_umap,
        patch("matome.engines.cluster.GaussianMixture") as mock_gmm,
    ):
        # Mock UMAP to return 2D linearly separable data
        reduced_a = [[0.0, 0.0], [0.1, 0.1], [0.0, 0.1]]
        reduced_b = [[10.0, 10.0], [10.1, 10.1], [10.0, 10.1]]
        mock_umap.return_value.fit_transform.return_value = np.array(reduced_a + reduced_b)

        # Mock GMM
        mock_gmm_instance = MagicMock()
        mock_gmm.return_value = mock_gmm_instance
        # predict_proba returns (N, K) probabilities
        probs = np.array([
            [0.99, 0.01], [0.99, 0.01], [0.99, 0.01],
            [0.01, 0.99], [0.01, 0.99], [0.01, 0.99]
        ])
        mock_gmm_instance.predict_proba.return_value = probs
        mock_gmm_instance.predict.return_value = np.array([0, 0, 0, 1, 1, 1])
        mock_gmm_instance.n_components = 2  # Simulate BIC finding 2
        mock_gmm_instance.bic.side_effect = [10.0, 20.0, 30.0, 40.0, 50.0]

        clusters = engine.cluster_nodes(embeddings, config)

        assert len(clusters) == 2

        # Verify grouping
        cluster_0 = next(c for c in clusters if c.id == 0)
        cluster_1 = next(c for c in clusters if c.id == 1)

        # Assuming cluster 0 and 1 are distinct, but their IDs might be swapped
        # Check that we have two sets of indices: {0,1,2} and {3,4,5}
        indices_set_0 = set(cluster_0.node_indices)
        indices_set_1 = set(cluster_1.node_indices)

        expected_sets = [{0, 1, 2}, {3, 4, 5}]
        assert indices_set_0 in expected_sets
        assert indices_set_1 in expected_sets
        assert indices_set_0 != indices_set_1


# Scenario 07: Single Cluster Edge Case
def test_scenario_07_single_cluster() -> None:
    embeddings = [[0.5] * 10]

    config = ProcessingConfig()
    engine = GMMClusterer()

    clusters = engine.cluster_nodes(embeddings, config)

    assert len(clusters) == 1
    assert clusters[0].id == 0
    assert clusters[0].node_indices == [0]
