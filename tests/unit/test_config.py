import os
from typing import Any
from unittest import mock

import pytest
from cryptography.fernet import Fernet
from pydantic import SecretStr, ValidationError

from src.domain_models import CredentialConfig, PipelineConfig


@pytest.fixture
def mock_env_key() -> Any:
    """Fixture to safely inject a valid encryption key for tests."""
    return mock.patch.dict(
        os.environ, {"MATOME_ENCRYPTION_KEY": Fernet.generate_key().decode("utf-8")}
    )


def test_credential_config_validation(mock_env_key: Any) -> None:
    """Verifies that CredentialConfig validates keys before encrypting them."""
    with mock_env_key:
        # Invalid length
        with pytest.raises(ValidationError, match="API key must be at least 20 characters long"):
            CredentialConfig(openrouter_api_key=SecretStr("sk-or-123"))

        # Invalid prefix
        with pytest.raises(ValidationError, match="API key must strictly match"):
            CredentialConfig(openrouter_api_key=SecretStr("sk-ant-12345678901234567890"))

        # Valid key encryption testing
        # The key must match the strict length and pattern sk-or-v1-[a-zA-Z0-9]{64}
        valid_key = "sk-or-v1-" + ("A" * 64)
        config = CredentialConfig(openrouter_api_key=SecretStr(valid_key))

        # Assert it was erased from memory in the pydantic model
        assert config.openrouter_api_key is None
        # Assert it was actually encrypted
        assert config._encrypted_api_key is not None
        assert config._encrypted_api_key != valid_key.encode("utf-8")

        # Assert we can retrieve it securely
        decrypted_secret = config.get_decrypted_api_key()
        assert decrypted_secret is not None
        assert decrypted_secret.get_secret_value() == valid_key


def test_credential_config_missing_key() -> None:
    """Verifies it fails fast if encryption key is missing from environment."""
    with mock.patch.dict(os.environ, {}, clear=True), pytest.raises(
        ValueError, match="MATOME_ENCRYPTION_KEY environment variable must be set"
    ):
        CredentialConfig()


def test_credential_config_loading(mock_env_key: Any) -> None:
    """Verifies that CredentialConfig correctly reads .env variables natively."""
    valid_key = "sk-or-v1-" + ("B" * 64)
    with mock_env_key, mock.patch.dict(os.environ, {"OPENROUTER_API_KEY": valid_key}):
        # Directly instantiate the unmodified production class, relying on os.environ directly
        # rather than dynamically altering `model_config` settings in a subclass.
        config = CredentialConfig()

        assert config.openrouter_api_key is None
        assert config._encrypted_api_key is not None

        decrypted = config.get_decrypted_api_key()
        assert decrypted is not None
        assert decrypted.get_secret_value() == valid_key


def test_pipeline_config_defaults(mock_env_key: Any) -> None:
    """Verifies PipelineConfig defaults."""
    with mock_env_key:
        config = PipelineConfig()
        assert config.max_chunk_scan_size == 10000
        assert config.fast_model == "google/gemini-2.5-flash"
        assert config.reasoning_model == "anthropic/claude-3.7-sonnet"
        assert config.multimodal_model == "openai/gpt-4o"
        assert config.trusted_model_hashes == []
        assert config.credentials is not None
        assert config.credentials.openrouter_api_key is None
        assert config.llm_service_path == "src.interfaces.LLMProtocol"
