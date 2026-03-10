import pytest
from pydantic import ValidationError

from src.domain_models import AppConfig, CredentialConfig, PipelineConfig


def test_pipeline_config_defaults() -> None:
    config = PipelineConfig()
    assert config.max_chunk_size == 5000
    assert config.max_file_size_bytes == 1024 * 1024 * 50
    assert config.clustering_random_seed == 42


def test_pipeline_config_validation() -> None:
    with pytest.raises(ValidationError):
        # max_chunk_size must be >= 100
        PipelineConfig(max_chunk_size=99)

    with pytest.raises(ValidationError):
        # max_file_size_bytes must be >= 1024
        PipelineConfig(max_file_size_bytes=100)


def test_credential_config_validation() -> None:
    # CredentialConfig accepts valid strings as SecretStr
    config = CredentialConfig(openrouter_api_key="test_key")  # type: ignore
    assert config.openrouter_api_key is not None
    assert config.openrouter_api_key.get_secret_value() == "test_key"


def test_app_config_forbid_extra() -> None:
    with pytest.raises(ValidationError):
        AppConfig(invalid_config="value")  # type: ignore
