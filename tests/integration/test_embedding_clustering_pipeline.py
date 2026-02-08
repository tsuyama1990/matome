from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from domain_models.config import ProcessingConfig
from domain_models.manifest import Chunk
from matome.engines.cluster import ClusterEngine
from matome.engines.embedder import EmbeddingService


@pytest.fixture
def sample_chunks():
    return [
        Chunk(index=0, text="Chunk 0", start_char_idx=0, end_char_idx=7),
        Chunk(index=1, text="Chunk 1", start_char_idx=8, end_char_idx=15),
    ]

@patch("matome.engines.embedder.SentenceTransformer")
@patch("matome.engines.cluster.UMAP")
@patch("matome.engines.cluster.GaussianMixture")
def test_full_pipeline(mock_gmm, mock_umap, mock_st, sample_chunks) -> None:
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
    embedder = EmbeddingService(config.embedding_model)
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
