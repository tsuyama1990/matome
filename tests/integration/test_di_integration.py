import pytest

from src.application.di_container import DIContainer
from src.domain_models.config import AppConfig
from src.interfaces.llm_protocol import LLMProtocol


class DummyLLMService(LLMProtocol):
    async def generate_text(self, prompt: str, model: str) -> str:
        return f"Mock response for {prompt}"



def test_di_integration_app_config(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-v1-testkeytestkeytestkeytestkeytestkey")
    monkeypatch.setenv("TENANT_ID", "test-tenant")

    config = AppConfig(openrouter_api_key="sk-or-v1-testkeytestkeytestkeytestkeytestkey", tenant_id="test-tenant") # type: ignore[arg-type]
    container = DIContainer()

    container.register_singleton(AppConfig, config)
    resolved_config = container.resolve(AppConfig)

    assert resolved_config is config
    assert resolved_config.tenant_id == "test-tenant"

def test_di_integration_mock_mode() -> None:
    container = DIContainer()

    # Simulate Mock Mode
    container.register_singleton(LLMProtocol, DummyLLMService()) # type: ignore[type-abstract]

    resolved_llm = container.resolve(LLMProtocol) # type: ignore[type-abstract]

    assert isinstance(resolved_llm, DummyLLMService)
