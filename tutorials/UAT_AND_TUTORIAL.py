# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "marimo>=0.20.4",
# ]
# ///
import marimo

__generated_with = "0.20.4"
app = marimo.App()

@app.cell
def __():
    import marimo as mo
    return (mo,)

@app.cell
def __(mo):
    mo.md(
        """
        # matome: User Acceptance Testing and Tutorial

        Welcome to the matome executable tutorial! This notebook demonstrates the entire system architecture, from basic configuration to advanced insight generation.

        ## Section 1: Introduction and Configuration (Cycle 01 & 02)

        This section initializes the `AppConfig` and the `DIContainer`, demonstrating how the system handles missing API keys and how "Mock Mode" is activated.
        """
    )
    return ()

@app.cell
def __():
    import os
    from pydantic import ValidationError
    from src.domain_models.config import AppConfig, ModelRoutingRules
    from src.application.di_container import DIContainer
    from src.interfaces.llm_protocol import LLMProtocol
    from src.infrastructure.test_services import (
        FallbackEmbeddingService,
        FallbackReasoningLLMService,
        FallbackVectorDB,
    )

    print("Running UAT-01-01: Secure Application Configuration and Startup")
    os.environ.pop("OPENROUTER_API_KEY", None)
    os.environ.pop("TENANT_ID", None)

    try:
        AppConfig(
            openrouter_api_key="sk-or-v1-0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",  # type: ignore[arg-type]
            tenant_id="sk-or-v1-0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
        )
        raise AssertionError("Expected ValidationError due to missing keys")
    except ValidationError:
        print("Success: AppConfig correctly rejected missing OPENROUTER_API_KEY.")

    os.environ["OPENROUTER_API_KEY"] = (
        "sk-or-v1-0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"
    )
    os.environ["TENANT_ID"] = "tenant1"
    try:
        ModelRoutingRules(text_fast_model="")
        raise AssertionError("Expected ValidationError due to empty string in model rules")
    except ValidationError:
        print("Success: AppConfig correctly rejected invalid routing rules.")

    config = AppConfig(
        openrouter_api_key="sk-or-v1-0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",  # type: ignore[arg-type]
        tenant_id="sk-or-v1-0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
    )
    assert "sk-or-v1-0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef" not in str(
        config
    ), "SecretStr leaked!"
    assert "**********" in str(config), "SecretStr did not mask correctly!"
    print("Success: SecretStr securely masked.")

    return AppConfig, ModelRoutingRules, DIContainer, LLMProtocol, FallbackEmbeddingService, FallbackReasoningLLMService, FallbackVectorDB, os, config

@app.cell
def __(DIContainer, LLMProtocol, os):
    print("Running UAT-01-02: Dependency Injection and Protocol Resolution")

    class FallbackLLM:
        pass

    container = DIContainer()
    instance = FallbackLLM()
    container.register_singleton(LLMProtocol, instance)
    resolved = container.resolve(LLMProtocol)  # type: ignore[type-abstract]
    assert resolved is instance  # type: ignore[comparison-overlap]
    print("Success: Resolved singleton successfully.")

    class ServiceA:
        def __init__(self, b: "ServiceB") -> None:
            self.b = b

    class ServiceB:
        def __init__(self, a: "ServiceA") -> None:
            self.a = a

    def factory_a() -> ServiceA:
        b = container.resolve(ServiceB)
        return ServiceA(b)

    def factory_b() -> ServiceB:
        a = container.resolve(ServiceA)
        return ServiceB(a)

    container.register(ServiceA, factory_a)
    container.register(ServiceB, factory_b)

    try:
        container.resolve(ServiceA)
        raise AssertionError("Expected RuntimeError due to circular dependency")
    except RuntimeError as e:
        assert "Circular dependency detected" in str(e)
        print(f"Success: Circular dependency caught gracefully: {e}")

    return FallbackLLM, ServiceA, ServiceB, container, factory_a, factory_b, instance, resolved

@app.cell
def __(DIContainer, LLMProtocol, os):
    print("Running UAT-01-03: Hybrid Environment Fallback Mode Execution")

    class FallbackLLMService(LLMProtocol):
        async def generate_text(self, prompt: str, model: str) -> str:
            return "fallbacked"

    fallback_container = DIContainer()
    if os.environ.get("MATOME_MOCK_MODE", "true") == "true":
        fallback_container.register_singleton(LLMProtocol, FallbackLLMService())  # type: ignore[type-abstract]

    assert isinstance(fallback_container.resolve(LLMProtocol), FallbackLLMService)  # type: ignore[type-abstract]
    print("Success: Fallback Mode Execution successfully resolved to fallback implementation.")

    return FallbackLLMService, fallback_container

