import os
from unittest import mock

import pytest
from pydantic import ValidationError

from src.config.settings import AppConfig, ModelConfig


def test_app_config_success(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test AppConfig loads correctly when env variables are provided."""

    with mock.patch.dict(
        os.environ,
        {},
        clear=True,
    ):
        config = AppConfig()
        assert config.environment == "production"


def test_database_config_success(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test DatabaseConfig loads correctly when env variables are provided."""
    from src.config.security import SecurityService
    from src.config.settings import DatabaseConfig

    encryption_key = "abcdefghijklmnopqrstuvwxyz12345678901234567="
    monkeypatch.setenv("ENCRYPTION_KEY", encryption_key)
    service = SecurityService()
    encrypted_uri = service.encrypt_key("postgresql://user:pass@localhost/db")

    with mock.patch.dict(
        os.environ,
        {"DATABASE_URI_ENCRYPTED": encrypted_uri, "ENCRYPTION_KEY": encryption_key},
        clear=True,
    ):
        config = DatabaseConfig()  # type: ignore[call-arg]
        with pytest.raises(ValueError, match="Local database connections are not permitted by current security policy."):
            config.get_decrypted_database_uri.get_secret_value()

        # Test valid external URI
        encrypted_valid_uri = service.encrypt_key("postgresql://user:pass@external.db.com/db")
        with mock.patch.dict(
            os.environ,
            {"DATABASE_URI_ENCRYPTED": encrypted_valid_uri, "ENCRYPTION_KEY": encryption_key},
            clear=True,
        ):
            config_valid = DatabaseConfig()  # type: ignore[call-arg]
            # Userinfo stripped check
            assert config_valid.get_decrypted_database_uri.get_secret_value() == "postgresql://external.db.com/db"



def test_model_config_success() -> None:
    """Test ModelConfig loads correctly with env vars."""
    with mock.patch.dict(
        os.environ,
        {
            "OPENROUTER_API_URL": "https://test.openrouter.ai/api",
            "TEXT_FAST_MODEL": "test-model-1",
            "TEXT_REASONING_MODEL": "test-model-2",
            "MULTIMODAL_MODEL": "test-model-3",
            "LLM_TIMEOUT": "45.0",
            "ALLOWED_HOSTS": '["test.openrouter.ai"]',
        },
        clear=True,
    ):
        config = ModelConfig()  # type: ignore[call-arg]
        assert str(config.openrouter_api_url) == "https://test.openrouter.ai/api"
        assert config.text_fast_model == "test-model-1"
        assert config.text_reasoning_model == "test-model-2"
        assert config.multimodal_model == "test-model-3"
        assert config.llm_timeout == 45.0


def test_model_config_invalid_url() -> None:
    """Test ModelConfig raises an error on non-HTTPS URLs."""
    with (
        mock.patch.dict(
            os.environ,
            {
                "OPENROUTER_API_URL": "http://test.openrouter.ai/api",
                "TEXT_FAST_MODEL": "test",
                "TEXT_REASONING_MODEL": "test",
                "MULTIMODAL_MODEL": "test",
            },
            clear=True,
        ),
        pytest.raises(ValidationError, match="must use HTTPS"),
    ):
        ModelConfig()  # type: ignore[call-arg]
