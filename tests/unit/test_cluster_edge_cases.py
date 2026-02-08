import numpy as np
import pytest

from domain_models.config import ProcessingConfig
from matome.engines.cluster import ClusterEngine


def test_cluster_engine_validation_nan() -> None:
    config = ProcessingConfig()
    engine = ClusterEngine(config)
    # NaN embedding
    embeddings = np.array([[np.nan, 0.1]])

    with pytest.raises(ValueError, match="Embeddings contain NaN or Infinity values"):
        engine.perform_clustering([0], embeddings)

def test_cluster_engine_validation_inf() -> None:
    config = ProcessingConfig()
    engine = ClusterEngine(config)
    # Inf embedding
    embeddings = np.array([[np.inf, 0.1]])

    with pytest.raises(ValueError, match="Embeddings contain NaN or Infinity values"):
        engine.perform_clustering([0], embeddings)

def test_cluster_engine_empty_input() -> None:
    config = ProcessingConfig()
    engine = ClusterEngine(config)
    # Empty chunks
    clusters = engine.perform_clustering([], np.array([]))
    assert clusters == []

    # Empty embeddings but chunks exist
    # Should perform clustering, but if embeddings is empty, logic might fail if not handled.
    # Added validation check for this.
    clusters = engine.perform_clustering([0], np.array([]))
    assert clusters == []
