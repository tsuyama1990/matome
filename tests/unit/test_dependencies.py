import uuid
from pathlib import Path

import pytest

from src.application import BaseTestChunkingService, BaseTestParsingService, build_ingestion_graph
from src.domain_models.document import EnrichedDocument
from src.domain_models.exceptions import ProcessingError
from src.domain_models.graph_state import GraphState, ProcessingStatus
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
    test_file = tmp_path / "test.txt"
    test_file.write_text("Hello World", encoding="utf-8")

    service = BaseTestParsingService()
    content = service.parse(str(test_file))

    assert content == "Hello World"


def test_base_test_parsing_service_file_not_found() -> None:
    """Test the base parsing service raises ProcessingError on missing file."""
    service = BaseTestParsingService()
    with pytest.raises(ProcessingError, match="File not found"):
        service.parse("/path/to/nonexistent/file.txt")


def test_base_test_chunking_service_success() -> None:
    """Test the base chunking service deterministically chunks text."""
    service = BaseTestChunkingService()
    text = "Sentence one. Sentence two! Sentence three?"

    chunks = service.chunk_text(text, source_file="test.txt")

    assert len(chunks) == 3
    assert chunks[0].content == "Sentence one."
    assert chunks[1].content == "Sentence two!"
    assert chunks[2].content == "Sentence three?"
    assert chunks[0].metadata.source_file == "test.txt"


def test_base_test_chunking_service_empty_text() -> None:
    """Test the base chunking service raises ProcessingError on empty text."""
    service = BaseTestChunkingService()
    with pytest.raises(ProcessingError, match="Cannot chunk empty text."):
        service.chunk_text("", source_file="test.txt")


def test_ingestion_workflow(tmp_path: Path) -> None:
    """Test the LangGraph ingestion workflow end-to-end."""
    # Setup test file
    test_file = tmp_path / "test_doc.txt"
    test_file.write_text("This is sentence one. And sentence two. Finally three.", encoding="utf-8")

    # Initialize GraphState
    doc_id = uuid.uuid4()
    doc = EnrichedDocument(document_id=doc_id, original_text=str(test_file))
    initial_state = GraphState(current_document=doc)

    # Build and run workflow
    workflow = build_ingestion_graph()

    # LangGraph invoke expects and returns the state dict
    final_state_dict = workflow.invoke(initial_state.model_dump())
    final_state = GraphState(**final_state_dict)

    # Assertions
    assert final_state.processing_status == ProcessingStatus.EMBEDDING
    assert final_state.current_document is not None
    assert "This is sentence one." in final_state.current_document.original_text

    # Ensure chunking occurred
    chunks = final_state.current_document.chunks
    assert len(chunks) == 3
    assert chunks[0].content == "This is sentence one."
    assert chunks[1].content == "And sentence two."
    assert chunks[2].content == "Finally three."
