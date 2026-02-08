import pytest
from pydantic import ValidationError

from domain_models.config import ProcessingConfig
from domain_models.manifest import Chunk, Cluster


def test_chunk_embedding_field() -> None:
    chunk = Chunk(
        index=0,
        text="test",
        start_char_idx=0,
        end_char_idx=4,
        embedding=[0.1, 0.2, 0.3]
    )
    assert chunk.embedding == [0.1, 0.2, 0.3]

def test_chunk_embedding_optional() -> None:
    chunk = Chunk(
        index=0,
        text="test",
        start_char_idx=0,
        end_char_idx=4
    )
    assert chunk.embedding is None

def test_config_embedding_model() -> None:
    config = ProcessingConfig()
    assert config.embedding_model == "intfloat/multilingual-e5-large"

    config = ProcessingConfig(embedding_model="other/model")
    assert config.embedding_model == "other/model"

def test_cluster_node_indices() -> None:
    cluster = Cluster(
        id=1,
        level=0,
        node_indices=[1, 2, 3]
    )
    assert cluster.node_indices == [1, 2, 3]
    assert cluster.id == 1
    assert cluster.level == 0

def test_invalid_config_parameters() -> None:
    # Test invalid embedding_batch_size (must be >= 1)
    with pytest.raises(ValidationError):
        ProcessingConfig(embedding_batch_size=0)

    # Test valid embedding_batch_size
    config = ProcessingConfig(embedding_batch_size=1)
    assert config.embedding_batch_size == 1

def test_config_factory_methods() -> None:
    # Test default()
    default_config = ProcessingConfig.default()
    assert default_config.max_tokens == 500
    assert default_config.overlap == 0
    assert default_config.embedding_model == "intfloat/multilingual-e5-large"
    assert default_config.clustering_algorithm == "gmm"

    # Test high_precision()
    hp_config = ProcessingConfig.high_precision()
    assert hp_config.max_tokens == 200
    assert hp_config.overlap == 20
    # Ensure defaults are preserved for others
    assert hp_config.embedding_model == "intfloat/multilingual-e5-large"
