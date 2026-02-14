import pytest
from pydantic import ValidationError

from domain_models.config import ProcessingConfig
from domain_models.constants import (
    DEFAULT_EMBEDDING,
    DEFAULT_MAX_TOKENS,
    DEFAULT_SEMANTIC_CHUNKING_MODE,
    DEFAULT_SEMANTIC_CHUNKING_PERCENTILE,
    DEFAULT_SEMANTIC_CHUNKING_THRESHOLD,
    DEFAULT_TOKENIZER,
)


def test_config_defaults() -> None:
    """Test that default configuration values are correctly set."""
    config = ProcessingConfig()

    assert config.max_tokens == DEFAULT_MAX_TOKENS
    assert config.tokenizer_model == DEFAULT_TOKENIZER
    assert config.semantic_chunking_mode == DEFAULT_SEMANTIC_CHUNKING_MODE
    assert config.semantic_chunking_threshold == DEFAULT_SEMANTIC_CHUNKING_THRESHOLD
    assert config.semantic_chunking_percentile == DEFAULT_SEMANTIC_CHUNKING_PERCENTILE
    assert config.embedding_model == DEFAULT_EMBEDDING


def test_config_validation_semantic_threshold() -> None:
    """Test validation logic for semantic chunking threshold."""
    # Valid range [0.0, 1.0]
    ProcessingConfig(semantic_chunking_mode=True, semantic_chunking_threshold=0.5)
    ProcessingConfig(semantic_chunking_mode=True, semantic_chunking_threshold=0.0)
    ProcessingConfig(semantic_chunking_mode=True, semantic_chunking_threshold=1.0)

    # Invalid range
    with pytest.raises(ValidationError):
        ProcessingConfig(semantic_chunking_mode=True, semantic_chunking_threshold=-0.1)

    with pytest.raises(ValidationError):
        ProcessingConfig(semantic_chunking_mode=True, semantic_chunking_threshold=1.1)


def test_config_embedding_model() -> None:
    """Test embedding model validation."""
    # Allowed model
    ProcessingConfig(embedding_model=DEFAULT_EMBEDDING)

    # Disallowed model
    with pytest.raises(ValidationError):
        ProcessingConfig(embedding_model="suspicious/model")


def test_config_factory_methods() -> None:
    """Test factory methods for creating specific configurations."""
    default_config = ProcessingConfig.default()
    assert isinstance(default_config, ProcessingConfig)

    high_precision = ProcessingConfig.high_precision()
    assert high_precision.max_tokens == 200
    assert high_precision.overlap == 20
