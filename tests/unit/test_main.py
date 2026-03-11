import os
import time
from pathlib import Path
from typing import Any
from unittest import mock

import pytest
from cryptography.fernet import Fernet

import main
from src.container import ProductionDIContainer
from src.document import DocumentProcessingServiceImpl
from src.domain_models import GraphState
from src.domain_models.constants import DEFAULT_MAX_CHUNK_SCAN_SIZE
from src.interfaces import ProcessingError


@pytest.fixture
def mock_env_key() -> Any:
    """Fixture to safely inject a valid encryption key for tests."""
    return mock.patch.dict(
        os.environ, {"MATOME_ENCRYPTION_KEY": Fernet.generate_key().decode("utf-8")}
    )


def test_init_container(mock_env_key: Any) -> None:
    with mock_env_key, mock.patch("src.container.resolve_class") as mock_resolve:
        # To test init_container without implementing services, we mock the resolve_class function
        # to just return our mock interfaces from test_container
        from tests.unit.test_container import (
            MockActiveLearningService,
            MockDocumentProcessingService,
            MockKnowledgeGraphService,
            MockLLMProtocol,
        )

        def llm_factory(*args: Any, **kwargs: Any) -> Any:
            return MockLLMProtocol()

        # Setup the mock to return specific classes based on the string passed
        def side_effect(path: str) -> Any:
            if "LLMProtocol" in path:
                return llm_factory
            if "DocumentProcessingService" in path:
                return MockDocumentProcessingService
            if "KnowledgeGraphService" in path:
                return MockKnowledgeGraphService
            if "ActiveLearningService" in path:
                return MockActiveLearningService
            if "DocumentProcessingServiceImpl" in path:
                return DocumentProcessingServiceImpl
            raise ValueError(path)

        mock_resolve.side_effect = side_effect

        container = main.init_container()
        assert isinstance(container, ProductionDIContainer)
        assert isinstance(container.llm_gateway, MockLLMProtocol)


def test_main_cli_help(capsys: pytest.CaptureFixture[str], mock_env_key: Any) -> None:
    with (
        mock_env_key,
        mock.patch("sys.argv", ["main.py"]),
        mock.patch("main.init_container") as mock_init,
    ):
        # We mock container so we don't try to instantiate abstract protocols
        mock_init.return_value = None
        result = main.main()
        assert result == 0
        captured = capsys.readouterr()
        assert "Hello from matome" in captured.out


def test_document_processing_workflow(tmp_path: Path) -> None:
    """Cycle 3: Tests the full LangGraph state transition and semantic chunking."""
    service = DocumentProcessingServiceImpl()

    # Create valid text file with Named Entities
    test_file = tmp_path / "valid_doc.txt"
    content = "The Quick Brown Fox jumps over the lazy dog. Microsoft and Apple are tech giants."
    test_file.write_text(content, encoding="utf-8")

    state = GraphState(file_path=str(test_file))

    # Process
    final_state = service.process(state)

    assert final_state.raw_text == content
    assert final_state.cleaned_text == content
    assert final_state.embedded_chunks is True

    # Ensure chunking worked and NER was extracted
    assert len(final_state.chunks) > 0

    all_entities = []
    for chunk in final_state.chunks:
        all_entities.extend(chunk.metadata.entities_extracted)

    assert "Quick Brown Fox" in all_entities or "The Quick Brown Fox" in all_entities
    assert "Microsoft" in all_entities
    assert "Apple" in all_entities


def test_document_processing_path_traversal() -> None:
    """Cycle 3: Verifies path traversal attacks raise ValueErrors immediately."""
    service = DocumentProcessingServiceImpl()

    malicious_path = "../../../../etc/passwd"
    state = GraphState(file_path=malicious_path)

    with pytest.raises(ValueError, match="Path traversal detected"):
        service.parse(state)


def test_document_processing_redos(tmp_path: Path) -> None:
    """Cycle 3: Verifies that semantic chunking bounds execution time (ReDoS mitigation)."""
    service = DocumentProcessingServiceImpl()

    test_file = tmp_path / "redos.txt"
    # Create an extremely long file of just a single repeated word
    content = "A " * (DEFAULT_MAX_CHUNK_SCAN_SIZE * 2)
    test_file.write_text(content, encoding="utf-8")

    state = GraphState(file_path=str(test_file))

    start_time = time.time()
    final_state = service.process(state)
    end_time = time.time()

    # It should chunk efficiently due to boundaries, rather than hanging exponentially
    assert end_time - start_time < 2.0
    assert len(final_state.chunks) >= 2


def test_document_processing_empty_file(tmp_path: Path) -> None:
    """Cycle 3: Asserts empty file produces empty chunks but completes gracefully."""
    service = DocumentProcessingServiceImpl()

    test_file = tmp_path / "empty.txt"
    test_file.write_text("", encoding="utf-8")

    state = GraphState(file_path=str(test_file))
    final_state = service.process(state)

    assert final_state.raw_text == ""
    assert final_state.cleaned_text == ""
    assert final_state.embedded_chunks is True
    assert len(final_state.chunks) == 0


def test_document_processing_file_not_found() -> None:
    """Cycle 3: Asserts file not found raises ProcessingError."""
    service = DocumentProcessingServiceImpl()
    state = GraphState(file_path="nonexistent_file.txt")

    with pytest.raises(ProcessingError, match="File not found"):
        service.parse(state)


def test_document_processing_stream(tmp_path: Path) -> None:
    """Cycle 3: Tests process_stream method."""
    service = DocumentProcessingServiceImpl()

    test_file = tmp_path / "stream_doc.txt"
    content = "Hello stream. World is good."
    test_file.write_text(content, encoding="utf-8")

    chunks = list(service.process_stream(str(test_file)))
    assert len(chunks) > 0
    assert "Hello stream." in chunks[0].text or "World is good." in chunks[-1].text
