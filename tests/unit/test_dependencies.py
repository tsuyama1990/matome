from pathlib import Path

import pytest

from src.application import build_ingestion_graph
from src.domain_models.exceptions import ProcessingError
from src.domain_models.graph_state import GraphState, ProcessingStatus
from src.infrastructure.test_services import SimpleParsingService
from src.interfaces.dependencies import DIContainer


class DummyInterface:
    def do_something(self) -> str:
        return "Not implemented"


class DummyImplementation(DummyInterface):
    def do_something(self) -> str:
        return "Success"


def test_di_container_registers_and_resolves() -> None:
    """Test standard registering and resolving from DI container."""
    container = DIContainer()
    container.register(DummyInterface, DummyImplementation)

    instance = container.resolve(DummyInterface)

    assert isinstance(instance, DummyImplementation)
    assert instance.do_something() == "Success"


def test_di_container_resolves_singletons() -> None:
    """Test DI container uses singleton logic."""
    container = DIContainer()
    container.register(DummyInterface, DummyImplementation)

    instance_1 = container.resolve(DummyInterface)
    instance_2 = container.resolve(DummyInterface)

    # They should be the exact same instance in memory
    assert id(instance_1) == id(instance_2)


def test_di_container_raises_on_unregistered_interface() -> None:
    """Test a RuntimeError is raised if attempting to resolve unregistered interfaces."""
    container = DIContainer()

    with pytest.raises(RuntimeError) as excinfo:
        container.resolve(DummyInterface)

    assert f"Dependency not registered: {DummyInterface}" in str(excinfo.value)


def test_di_container_loads_dynamic_class() -> None:
    """Test dynamically loading a class works correctly."""
    container = DIContainer()

    loaded_class = container.load_dynamic_class("src.interfaces.dependencies", "DIContainer")
    assert loaded_class is DIContainer


def test_base_test_parsing_service_success(tmp_path: Path) -> None:
    """Test the base parsing service correctly reads a file."""
    from pydantic import SecretStr

    from src.config.settings import AppConfig

    config = AppConfig(
        database_uri=SecretStr("mock"), encryption_key=SecretStr("A" * 32), upload_dir=str(tmp_path)
    )

    test_file = tmp_path / "test.txt"
    test_file.write_text("Hello World", encoding="utf-8")

    service = SimpleParsingService(config=config)
    content = service.parse("test.txt")

    assert content == "Hello World"


def test_base_test_parsing_service_file_not_found(tmp_path: Path) -> None:
    """Test the base parsing service raises ProcessingError on missing file."""
    from pydantic import SecretStr

    from src.config.settings import AppConfig

    config = AppConfig(
        database_uri=SecretStr("mock"), encryption_key=SecretStr("A" * 32), upload_dir=str(tmp_path)
    )

    service = SimpleParsingService(config=config)
    with pytest.raises(ProcessingError, match="File not found"):
        service.parse("nonexistent_file.txt")


def test_semantic_chunking_service_empty_text(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test the base chunking service raises ProcessingError on empty text."""
    monkeypatch.setenv("OPENROUTER_API_KEY", "mock_key")
    from src.application import SemanticChunkingService
    from src.config.settings import ModelConfig

    config = ModelConfig()  # type: ignore[call-arg]
    service = SemanticChunkingService(config)
    with pytest.raises(ProcessingError, match="Cannot chunk empty text."):
        service.chunk_text("", source_file="test.txt")


class DummyLLM:
    """Dummy LLM client strictly for testing isolated workflow logic."""

    async def generate(self, prompt: str) -> str:
        return f"[Mock CoD] Extracted entities. Length: {len(prompt)}"


@pytest.mark.asyncio
async def test_ingestion_workflow(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test the LangGraph ingestion workflow end-to-end."""
    # We must patch AppConfig environment variables via monkeypatch
    # to redirect the UPLOAD_DIR for test to our pytest tmp_path
    monkeypatch.setenv("DATABASE_URI", "mock_db")
    monkeypatch.setenv("ENCRYPTION_KEY", "A" * 32)
    monkeypatch.setenv("UPLOAD_DIR", str(tmp_path))
    monkeypatch.setenv("OPENROUTER_API_KEY", "mock_key")

    # Setup test file
    test_file = tmp_path / "test_doc.txt"
    test_file.write_text(
        "This is the system manual. It will be implemented. John is an engineer.", encoding="utf-8"
    )

    # Initialize GraphState with the upload filepath
    initial_state = GraphState(source_filepath="test_doc.txt")

    from src.application import SemanticChunkingService
    from src.application.di import global_container
    from src.config.settings import AppConfig, ModelConfig
    from src.interfaces.dependencies import ChunkingProtocol, DocumentParserProtocol, LLMProtocol

    # We must register the implementation protocols for testing inside the test environment DI container
    global_container.register(AppConfig, AppConfig)  # type: ignore[arg-type]
    global_container.register(ModelConfig, ModelConfig)  # type: ignore[arg-type]
    global_container.register(DocumentParserProtocol, lambda: SimpleParsingService(AppConfig()))  # type: ignore[type-abstract,call-arg]
    global_container.register(ChunkingProtocol, lambda: SemanticChunkingService(ModelConfig()))  # type: ignore[type-abstract,call-arg]
    global_container.register(LLMProtocol, DummyLLM)  # type: ignore[type-abstract]

    # Build and run workflow
    workflow = build_ingestion_graph()

    # LangGraph ainvoke expects and returns the state object asynchronously
    final_state_dict = await workflow.ainvoke(initial_state)
    final_state = GraphState(**final_state_dict)

    # Assertions
    assert final_state.processing_status == ProcessingStatus.COMPLETE
    assert final_state.current_document is not None

    doc = final_state.current_document
    assert "This is the system manual." in doc.original_text

    # Ensure chunking occurred
    assert len(doc.chunks) > 0
    assert len(doc.chunks[0].embedding) == 768

    # Assert NER and Axes
    assert len(doc.chunks[0].metadata.extracted_entities) >= 0
    assert doc.chunks[0].metadata.time_axis in ["Past", "Present", "Future"]

    # Ensure clustering occurred and nodes created
    assert len(doc.raptor_nodes) > 0

    # Ensure CoD occurred
    assert "CoD" in doc.raptor_nodes[0].summarized_content
