import pytest

from src.di_container import DIContainer, EnvCredentialProvider
from src.domain_models import AppConfig, PipelineConfig


def test_env_credential_provider(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENROUTER_API_KEY", "secret-test-key")
    provider = EnvCredentialProvider()

    api_key = provider.get_openrouter_api_key()
    assert api_key is not None
    assert api_key.get_secret_value() == "secret-test-key"


def test_env_credential_provider_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    provider = EnvCredentialProvider()

    api_key = provider.get_openrouter_api_key()
    assert api_key is None


def test_di_container_init(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PIPELINE__MAX_CHUNK_SIZE", "2000")
    monkeypatch.setenv("APP_ENV", "production")

    container = DIContainer()
    config = container.get_config()

    assert isinstance(config, AppConfig)
    assert config.environment == "production"
    assert isinstance(config.pipeline, PipelineConfig)
    assert config.pipeline.max_chunk_size == 2000

    provider = container.get_credential_provider()
    assert isinstance(provider, EnvCredentialProvider)

    assert container.document_repo is None
    assert container.user_repo is None
    assert container.vector_db is None
    assert container.ai_gateway is None
