import pytest

from src.interfaces.dependencies import DIContainer


class TestProtocol:
    def do_something(self) -> str:
        return "Not implemented"


class TestService(TestProtocol):
    def do_something(self) -> str:
        return "Success"


def test_di_container_registers_and_resolves() -> None:
    """Test standard registering and resolving from DI container."""
    container = DIContainer()
    container.register(TestProtocol, TestService)

    instance = container.resolve(TestProtocol)

    assert isinstance(instance, TestService)
    assert instance.do_something() == "Success"


def test_di_container_resolves_singletons() -> None:
    """Test DI container uses singleton logic."""
    container = DIContainer()
    container.register(TestProtocol, TestService)

    instance_1 = container.resolve(TestProtocol)
    instance_2 = container.resolve(TestProtocol)

    # They should be the exact same instance in memory
    assert id(instance_1) == id(instance_2)


def test_di_container_raises_on_unregistered_interface() -> None:
    """Test a RuntimeError is raised if attempting to resolve unregistered interfaces."""
    container = DIContainer()

    with pytest.raises(RuntimeError) as excinfo:
        container.resolve(TestProtocol)

    assert f"Dependency not registered: {TestProtocol}" in str(excinfo.value)


def test_di_container_loads_dynamic_class() -> None:
    """Test dynamically loading a class works correctly."""
    container = DIContainer()

    loaded_class = container.load_dynamic_class("src.interfaces.dependencies", "DIContainer")
    assert loaded_class is DIContainer


def test_validate_container_fails() -> None:
    from src.interfaces.dependencies import validate_container

    container = DIContainer()
    import pytest

    with pytest.raises(RuntimeError):
        validate_container(container)


def test_bootstrap_application_services() -> None:
    from typing import Any

    from pydantic import SecretStr

    from src.config.settings import AppConfig as SettingsAppConfig
    from src.domain_models.config import AppConfig as DomainAppConfig
    from src.infrastructure.test_services import (
        FallbackEmbeddingService,
        FallbackLLMService,
        PlainTextParser,
        SafeTestDocumentRepository,
    )
    from src.interfaces.dependencies import (
        EmbeddingProtocol,
        LLMProtocol,
        TextParserProtocol,
        VectorStoreProtocol,
        bootstrap_application_services,
    )

    class FallbackVectorStore:
        def upsert(self, collection_name: str, records: list[Any]) -> None:
            return None

        def search(self, collection_name: str, query_vector: list[Any], limit: int) -> list[Any]:
            return []

    container = DIContainer()

    # Pre-register required protocols
    container.register(LLMProtocol, FallbackLLMService)  # type: ignore[type-abstract]
    container.register(VectorStoreProtocol, FallbackVectorStore)  # type: ignore[type-abstract]
    container.register(EmbeddingProtocol, FallbackEmbeddingService)  # type: ignore[type-abstract]
    container.register(TextParserProtocol, PlainTextParser)  # type: ignore[type-abstract]

    # Pre-register configs
    container.register(SettingsAppConfig, SettingsAppConfig)
    container.register(
        DomainAppConfig, lambda: DomainAppConfig(openrouter_api_key=SecretStr("a"), tenant_id="b")
    )

    bootstrap_application_services(container)

    # Now try to resolve the services
    from src.application import IngestionPipeline, NLPService, RaptorEngine, SQ3REngine
    from src.interfaces.dependencies import PivotWorkflowProtocol, VectorDBProtocol
    from src.interfaces.repository import DocumentRepositoryProtocol

    container.register(DocumentRepositoryProtocol, SafeTestDocumentRepository)  # type: ignore[type-abstract]

    raptor = container.resolve(RaptorEngine)
    assert raptor is not None

    sq3r = container.resolve(SQ3REngine)
    assert sq3r is not None

    pivot = container.resolve(PivotWorkflowProtocol)  # type: ignore[type-abstract]
    assert pivot is not None

    vdb = container.resolve(VectorDBProtocol)  # type: ignore[type-abstract]
    assert vdb is not None

    nlp = container.resolve(NLPService)
    assert nlp is not None

    ingest = container.resolve(IngestionPipeline)
    assert ingest is not None
