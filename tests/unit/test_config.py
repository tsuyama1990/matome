import pytest
from pydantic import ValidationError

from src.config.settings import AppConfig, ModelConfig


def test_app_config_success(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test AppConfig loads correctly when env variables are provided."""
    # Ensure no variables are loaded
    monkeypatch.delenv("OPENROUTER_API_URL", raising=False)
    monkeypatch.delenv("TEXT_FAST_MODEL", raising=False)
    monkeypatch.delenv("TEXT_REASONING_MODEL", raising=False)

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

    monkeypatch.setenv("DATABASE_URI_ENCRYPTED", encrypted_uri)
    config = DatabaseConfig()  # type: ignore[call-arg]
    with pytest.raises(
        ValueError, match="Local database connections are not permitted by security policy."
    ):
        config.get_decrypted_database_uri.get_secret_value()

    # Test valid external URI
    encrypted_valid_uri = service.encrypt_key("postgresql://user:pass@external.db.com/db")
    monkeypatch.setenv("DATABASE_URI_ENCRYPTED", encrypted_valid_uri)

    config_valid = DatabaseConfig()  # type: ignore[call-arg]
    # Userinfo stripped check
    assert (
        config_valid.get_decrypted_database_uri.get_secret_value()
        == "postgresql://external.db.com/db"
    )


def test_model_config_success(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test ModelConfig loads correctly with env vars."""
    monkeypatch.setenv("OPENROUTER_API_URL", "https://test.openrouter.ai/api")
    monkeypatch.setenv("TEXT_FAST_MODEL", "test-model-1")
    monkeypatch.setenv("TEXT_REASONING_MODEL", "test-model-2")
    monkeypatch.setenv("MULTIMODAL_MODEL", "test-model-3")
    monkeypatch.setenv("LLM_TIMEOUT", "45.0")
    monkeypatch.setenv("ALLOWED_HOSTS", '["test.openrouter.ai"]')

    config = ModelConfig()  # type: ignore[call-arg]
    assert str(config.openrouter_api_url) == "https://test.openrouter.ai/api"
    assert config.text_fast_model == "test-model-1"
    assert config.text_reasoning_model == "test-model-2"
    assert config.multimodal_model == "test-model-3"
    assert config.llm_timeout == 45.0


def test_model_config_invalid_url(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test ModelConfig raises an error on non-HTTPS URLs."""
    monkeypatch.setenv("OPENROUTER_API_URL", "http://test.openrouter.ai/api")
    monkeypatch.setenv("TEXT_FAST_MODEL", "test")
    monkeypatch.setenv("TEXT_REASONING_MODEL", "test")
    monkeypatch.setenv("MULTIMODAL_MODEL", "test")

    with pytest.raises(ValidationError, match="must use HTTPS"):
        ModelConfig()  # type: ignore[call-arg]
