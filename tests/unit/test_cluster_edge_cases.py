import numpy as np
import pytest

from domain_models.config import ProcessingConfig
from matome.engines.cluster import GMMClusterer


def test_cluster_engine_validation_nan() -> None:
    config = ProcessingConfig()
    engine = GMMClusterer()
    # NaN embedding
    embeddings = [[np.nan, 0.1]]

    with pytest.raises(ValueError, match="Embeddings contain NaN or Infinity values"):
        engine.cluster_nodes(embeddings, config)

def test_cluster_engine_validation_inf() -> None:
    config = ProcessingConfig()
    engine = GMMClusterer()
    # Inf embedding
    embeddings = [[np.inf, 0.1]]

    with pytest.raises(ValueError, match="Embeddings contain NaN or Infinity values"):
        engine.cluster_nodes(embeddings, config)

def test_cluster_engine_empty_input() -> None:
    config = ProcessingConfig()
    engine = GMMClusterer()
    # Empty chunks
    clusters = engine.cluster_nodes([], config)
    assert clusters == []

    # Empty embeddings but chunks exist - API takes only embeddings
    clusters = engine.cluster_nodes([], config)
    assert clusters == []
