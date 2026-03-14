import pytest

from src.application.di_container import DIContainer
from src.domain_models.config import AppConfig, ModelRoutingRules
from src.infrastructure.openrouter import OpenRouterClient
from src.infrastructure.test_services import DummyLLMService
from src.interfaces.llm_protocol import LLMProtocol


@pytest.fixture
def test_config(monkeypatch: pytest.MonkeyPatch) -> AppConfig:
    monkeypatch.setenv(
        "OPENROUTER_API_KEY",
        "sk-or-v1-abcdef0123456789abcdef0123456789abcdef0123456789abcdef0123456789",
    )
    monkeypatch.setenv("TENANT_ID", "test-tenant")
    return AppConfig(  # type: ignore[call-arg]
        routing_rules=ModelRoutingRules(
            text_fast_model="fast-model",
            text_reasoning_model="reasoning-model",
            multimodal_model="vision-model",
            fallback_model="fallback-model",
        )
    )


def test_di_resolves_openrouter_client(test_config: AppConfig) -> None:
    container = DIContainer()
    container.register_singleton(AppConfig, test_config)

    def llm_factory() -> LLMProtocol:
        config = container.resolve(AppConfig)
        return OpenRouterClient(config)

    container.register(LLMProtocol, llm_factory)  # type: ignore[type-abstract]

    llm = container.resolve(LLMProtocol)  # type: ignore[type-abstract]

    assert isinstance(llm, OpenRouterClient)
    assert llm._config == test_config


def test_di_resolves_mock_mode(test_config: AppConfig) -> None:
    container = DIContainer()
    container.register_singleton(AppConfig, test_config)

    def llm_factory() -> LLMProtocol:
        return DummyLLMService()

    container.register(LLMProtocol, llm_factory)  # type: ignore[type-abstract]

    llm = container.resolve(LLMProtocol)  # type: ignore[type-abstract]

    assert isinstance(llm, DummyLLMService)
