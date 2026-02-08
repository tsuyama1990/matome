from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from domain_models.config import ProcessingConfig
from domain_models.manifest import Chunk
from matome.engines.cluster import ClusterEngine
from matome.engines.embedder import EmbeddingService


@pytest.fixture
def sample_chunks() -> list[Chunk]:
    return [
        Chunk(index=0, text="Chunk 0", start_char_idx=0, end_char_idx=7),
        Chunk(index=1, text="Chunk 1", start_char_idx=8, end_char_idx=15),
    ]

@patch("matome.engines.embedder.SentenceTransformer")
@patch("matome.engines.cluster.UMAP")
@patch("matome.engines.cluster.GaussianMixture")
def test_full_pipeline_mocked(mock_gmm: MagicMock, mock_umap: MagicMock, mock_st: MagicMock, sample_chunks: list[Chunk]) -> None:
    # Setup mocks
    mock_st_instance = MagicMock()
    mock_st.return_value = mock_st_instance
    mock_st_instance.encode.return_value = np.array([[0.1]*10]*2) # 2 chunks, 10 dim

    mock_umap_instance = MagicMock()
    mock_umap.return_value = mock_umap_instance
    mock_umap_instance.fit_transform.return_value = np.array([[0.1, 0.1], [0.9, 0.9]])

    mock_gmm_instance = MagicMock()
    mock_gmm.return_value = mock_gmm_instance
    mock_gmm_instance.predict.return_value = np.array([0, 1])
    mock_gmm_instance.n_components = 2
    mock_gmm_instance.bic.side_effect = [10.0, 20.0, 30.0]

    # Run pipeline
    config = ProcessingConfig()

    # 1. Embedding
    embedder = EmbeddingService(config)
    chunks_with_embeddings = embedder.embed_chunks(sample_chunks)

    assert chunks_with_embeddings[0].embedding is not None

    # 2. Clustering
    cluster_engine = ClusterEngine(config)
    embeddings = np.array([c.embedding for c in chunks_with_embeddings])
    clusters = cluster_engine.perform_clustering(chunks_with_embeddings, embeddings)

    assert len(clusters) == 2
    assert clusters[0].id == 0
    assert clusters[0].node_indices == [0]
    assert clusters[1].id == 1
    assert clusters[1].node_indices == [1]

@pytest.mark.skip(reason="Requires external model download, potentially slow")
def test_real_pipeline_small() -> None:
    # This test runs without mocks using a small model
    # Use 'paraphrase-MiniLM-L3-v2' which is very small

    chunks = [
        Chunk(index=0, text="Apple pie recipe", start_char_idx=0, end_char_idx=16),
        Chunk(index=1, text="Python programming", start_char_idx=17, end_char_idx=35),
        Chunk(index=2, text="Baking cakes", start_char_idx=36, end_char_idx=48),
        Chunk(index=3, text="Code debugging", start_char_idx=49, end_char_idx=63),
    ]

    config = ProcessingConfig(
        embedding_model="sentence-transformers/all-MiniLM-L6-v2", # Small model
        n_clusters=2 # Force 2 clusters
    )

    # 1. Real Embedding
    try:
        embedder = EmbeddingService(config)
        chunks = embedder.embed_chunks(chunks)
    except Exception as e:
        pytest.skip(f"Skipping real embedding test due to model load failure: {e}")

    assert chunks[0].embedding is not None

    # 2. Real Clustering
    # With 4 samples, UMAP might need help.
    cluster_engine = ClusterEngine(config)
    embeddings = np.array([c.embedding for c in chunks])

    # Use n_neighbors=2 for small dataset
    clusters = cluster_engine.perform_clustering(chunks, embeddings, n_neighbors=2)

    assert len(clusters) == 2
    # Check that similar items are grouped together
    # Indices 0 (Apple) and 2 (Baking) should be together
    # Indices 1 (Python) and 3 (Code) should be together

    # Find cluster containing 0
    c0_id = next(c.id for c in clusters if 0 in c.node_indices)
    assert 2 in next(c.node_indices for c in clusters if c.id == c0_id)

    # Find cluster containing 1
    c1_id = next(c.id for c in clusters if 1 in c.node_indices)
    assert 3 in next(c.node_indices for c in clusters if c.id == c1_id)

    assert c0_id != c1_id
