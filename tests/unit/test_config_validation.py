import pytest
from pydantic import ValidationError

from domain_models.config import ProcessingConfig


def test_config_defaults_valid() -> None:
    """Ensure default configuration is valid."""
    config = ProcessingConfig()
    assert config.embedding_model
    assert config.tokenizer_model


def test_embedding_model_validation() -> None:
    """Test embedding model validation."""
    # Empty string
    with pytest.raises(ValidationError):
        ProcessingConfig(embedding_model="")

    # Whitespace
    with pytest.raises(ValidationError):
        ProcessingConfig(embedding_model="   ")

    # Injection chars
    with pytest.raises(ValidationError):
        ProcessingConfig(embedding_model="model; rm -rf")


def test_tokenizer_model_validation() -> None:
    """Test tokenizer model validation against whitelist."""
    # Valid
    config = ProcessingConfig(tokenizer_model="cl100k_base")
    assert config.tokenizer_model == "cl100k_base"

    # Invalid
    with pytest.raises(ValidationError) as exc:
        ProcessingConfig(tokenizer_model="invalid_model")
    assert "not allowed" in str(exc.value)
