import os
from pathlib import Path
from typing import Any
from unittest import mock

import pytest
from cryptography.fernet import Fernet
from pydantic import SecretStr, ValidationError

from src.domain_models.config import ApiCredentials, PipelineConfig


@pytest.fixture
def mock_env_key() -> Any:
    """Fixture to safely inject a valid encryption key for tests."""
    return mock.patch.dict(
        os.environ, {"MATOME_ENCRYPTION_KEY": Fernet.generate_key().decode("utf-8")}
    )


def test_api_credentials_validation(mock_env_key: Any) -> None:
    """Verifies that ApiCredentials validates keys before encrypting them."""
    with mock_env_key:
        # Invalid length
        with pytest.raises(ValidationError, match="API key must be at least 20 characters long"):
            ApiCredentials(openrouter_api_key=SecretStr("sk-or-123"))

        # Invalid prefix
        with pytest.raises(ValidationError, match="API key must strictly match"):
            ApiCredentials(openrouter_api_key=SecretStr("sk-ant-12345678901234567890"))

        # Valid key encryption testing
        # The key must match the strict length and pattern sk-or-v1-[a-zA-Z0-9]{64}
        valid_key = "sk-or-v1-" + ("A" * 64)
        config = ApiCredentials(openrouter_api_key=SecretStr(valid_key))

        from src.infrastructure.crypto import CryptoService

        crypto_service = CryptoService(config.crypto_config)
        config.encrypt_key(crypto_service)

        # Assert it was erased from memory in the pydantic model
        assert config.openrouter_api_key is None
        # Assert it was actually encrypted
        assert config.encrypted_key is not None
        assert config.encrypted_key != valid_key.encode("utf-8")

        # Assert we can retrieve it securely
        decrypted_secret = config.get_decrypted_api_key(crypto_service)
        assert decrypted_secret is not None
        assert decrypted_secret.get_secret_value() == valid_key


def test_api_credentials_missing_key() -> None:
    """Verifies it fails fast if encryption key is missing from environment."""
    valid_key = "sk-or-v1-" + ("B" * 64)
    with mock.patch.dict(os.environ, {}, clear=True):
        config = ApiCredentials(openrouter_api_key=SecretStr(valid_key))
        from src.infrastructure.crypto import CryptoService

        with pytest.raises(
            ValueError, match="MATOME_ENCRYPTION_KEY environment variable must be set"
        ):
            CryptoService(config.crypto_config)


def test_api_credentials_loading(mock_env_key: Any, tmp_path: Path) -> None:
    """Verifies that ApiCredentials correctly reads .env variables natively via file."""
    valid_key = "sk-or-v1-" + ("B" * 64)

    with mock_env_key:
        with mock.patch.dict(os.environ, {"OPENROUTER_API_KEY": valid_key}):
            config = ApiCredentials()

            from src.infrastructure.crypto import CryptoService

            crypto_service = CryptoService(config.crypto_config)
            config.encrypt_key(crypto_service)

        assert config.openrouter_api_key is None
        assert config.encrypted_key is not None

        decrypted = config.get_decrypted_api_key(crypto_service)
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
        assert config.credentials.crypto_config.crypto_hash_algorithm == "sha256"
        assert config.llm_service_path == "src.interfaces.LLMProtocol"
        assert config.app_domain == "https://matome.test"
        assert config.app_title == "matome"
        assert config.max_prompt_length == 1000000
        assert config.requests_per_minute_limit == 60


def test_pipeline_config_ssrf_crlf_protections(mock_env_key: Any) -> None:
    """Verifies PipelineConfig strict SSRF and CRLF protections."""
    with mock_env_key:
        with pytest.raises(ValidationError, match="CRLF injection detected in header value."):
            PipelineConfig(app_title="matome\nadmin")

        with pytest.raises(ValidationError, match="Endpoint must use HTTPS."):
            PipelineConfig(openrouter_endpoint="http://openrouter.ai/api")

        with pytest.raises(
            ValidationError,
            match="Domain https://evil.com is not in the allowed API domains whitelist.",
        ):
            PipelineConfig(openrouter_endpoint="https://evil.com/api")

        # Verify custom whitelist works with custom endpoint
        config = PipelineConfig(
            allowed_api_domains=["https://custom.com"],
            openrouter_endpoint="https://custom.com/v1/chat",
        )
        assert config.openrouter_endpoint == "https://custom.com/v1/chat"
