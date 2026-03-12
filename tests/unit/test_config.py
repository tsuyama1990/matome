import os
from unittest import mock

import pytest
from cryptography.fernet import Fernet
from pydantic import SecretStr, ValidationError

from src.domain_models.config import ApiCredentials, CredentialConfig, CryptoConfig, CryptoService


def test_crypto_config_valid_key() -> None:
    valid_key = Fernet.generate_key().decode("utf-8")
    with mock.patch.dict(os.environ, {"MATOME_ENCRYPTION_KEY": valid_key}):
        config = CryptoConfig()  # type: ignore[call-arg]
        assert config.matome_encryption_key == valid_key

def test_crypto_config_invalid_key() -> None:
    invalid_key = "invalid_key_length"
    with mock.patch.dict(os.environ, {"MATOME_ENCRYPTION_KEY": invalid_key}), pytest.raises(
        ValidationError
    ):
        CryptoConfig()  # type: ignore[call-arg]

def test_credential_config_yield_and_clear_secret() -> None:
    test_key = "test_openrouter_api_key_123"
    with mock.patch.dict(os.environ, {"OPENROUTER_API_KEY": test_key}):
        config = CredentialConfig()  # type: ignore[call-arg]

        with config.yield_and_clear_secret() as secret:
            assert secret == test_key

        # After context, the secret should be cleared
        assert config.openrouter_api_key.get_secret_value() == ""

def test_api_credentials() -> None:
    creds = ApiCredentials(encrypted_key=SecretStr("my_secret"))
    assert creds.encrypted_key.get_secret_value() == "my_secret"

def test_crypto_service_valid() -> None:
    valid_key = Fernet.generate_key().decode("utf-8")
    service = CryptoService(valid_key)

    test_data = "my_sensitive_data"
    encrypted = service.encrypt(test_data)

    assert encrypted != test_data
    assert service.decrypt(encrypted) == test_data

def test_crypto_service_invalid_key_length() -> None:
    with pytest.raises(ValueError, match="Invalid encryption key"):
        CryptoService("too_short")
