from pathlib import Path

import pytest
from pydantic import ValidationError

from src.domain_models.config import CredentialConfig, PipelineConfig


def test_pipeline_config_defaults() -> None:
    config = PipelineConfig()
    assert config.max_chunk_scan_size == 65536
    assert config.text_fast_model == "google/gemini-2.5-flash"


def test_pipeline_config_extra_forbid() -> None:
    with pytest.raises(ValidationError):
        PipelineConfig(extra_field="invalid")  # type: ignore[call-arg]


def test_pipeline_config_invalid_chunk_size() -> None:
    with pytest.raises(ValidationError):
        PipelineConfig(max_chunk_scan_size=500)


def test_credential_config_loads_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENROUTER_API_KEY", "test_key")
    config = CredentialConfig()
    assert config.openrouter_api_key is not None
    assert config.openrouter_api_key.get_secret_value() == "test_key"


def test_credential_config_extra_forbid() -> None:
    with pytest.raises(ValidationError):
        CredentialConfig(extra_field="invalid")  # type: ignore[call-arg]


def test_pipeline_config_from_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text("MAX_CHUNK_SCAN_SIZE=2048\n")

    # Temporarily remove variable from environment so it strictly falls back to the .env file loading
    monkeypatch.delenv("MAX_CHUNK_SCAN_SIZE", raising=False)

    # Force pydantic-settings to read the new explicit env file
    config = PipelineConfig(_env_file=env_file) # type: ignore[call-arg]
    assert config.max_chunk_scan_size == 2048
