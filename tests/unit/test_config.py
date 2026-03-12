"""Unit tests for config."""

import os
from unittest import mock

import pytest
from pydantic import ValidationError

from src.domain_models.config import (
    CredentialConfig,
    CryptoConfig,
    CryptoService,
    PipelineConfig,
)


def test_crypto_config_valid() -> None:
    """Test CryptoConfig loads properly."""
    with mock.patch.dict(os.environ, {"MATOME_ENCRYPTION_KEY": "test_key"}):
        config = CryptoConfig()  # type: ignore[call-arg]
        assert config.matome_encryption_key == "test_key"


def test_crypto_config_missing_key() -> None:
    """Test CryptoConfig raises ValidationError if missing key."""
    with mock.patch.dict(os.environ, clear=True), pytest.raises(ValidationError):
        CryptoConfig()  # type: ignore[call-arg]


def test_crypto_service() -> None:
    """Test CryptoService encryption and decryption."""
    # Create a valid 32 url-safe base64-encoded key
    from cryptography.fernet import Fernet

    key = Fernet.generate_key().decode("utf-8")
    service = CryptoService(key=key)

    data = "test_data"
    encrypted = service.encrypt(data)
    assert encrypted != data

    decrypted = service.decrypt(encrypted)
    assert decrypted == data


def test_credential_config_and_api_credentials() -> None:
    """Test CredentialConfig and ApiCredentials context manager."""
    with mock.patch.dict(os.environ, {"OPENROUTER_API_KEY": "test_api_key"}):
        config = CredentialConfig()  # type: ignore[call-arg]
        from cryptography.fernet import Fernet

        key = Fernet.generate_key().decode("utf-8")
        service = CryptoService(key=key)

        api_creds = config.get_api_credentials(service)
        assert api_creds.encrypted_key != "test_api_key"

        with api_creds.get_decrypted_key(service) as decrypted_key:
            assert decrypted_key == "test_api_key"


def test_pipeline_config() -> None:
    """Test PipelineConfig default values."""
    with mock.patch.dict(os.environ, clear=True):
        config = PipelineConfig()
        assert config.llm_gateway_path == "src.infrastructure.llm_gateway.LLMGateway"
