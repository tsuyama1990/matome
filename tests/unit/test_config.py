import pytest
from pydantic import ValidationError

from src.domain_models.config import CredentialConfig, PipelineConfig


def test_pipeline_config_valid() -> None:
    config = PipelineConfig(
        max_chunk_scan_size=70000,
        trusted_model_hashes=["hash1"],
        text_fast_model="model_a",
        text_reasoning_model="model_b",
        multimodal_model="model_c",
    )
    assert config.max_chunk_scan_size == 70000
    assert config.text_fast_model == "model_a"


def test_pipeline_config_invalid_extra() -> None:
    with pytest.raises(ValidationError):
        PipelineConfig(unknown_field="test")  # type: ignore


def test_pipeline_config_invalid_ge() -> None:
    with pytest.raises(ValidationError):
        PipelineConfig(max_chunk_scan_size=10)


def test_credential_config_valid() -> None:
    config = CredentialConfig(openrouter_api_key="secret")
    assert config.openrouter_api_key is not None
    assert config.openrouter_api_key.get_secret_value() == "secret"


def test_credential_config_invalid_extra() -> None:
    with pytest.raises(ValidationError):
        CredentialConfig(unknown_field="test")  # type: ignore
