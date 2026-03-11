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
from src.interfaces import (
    ActiveLearningService,
    DocumentProcessingService,
    KnowledgeGraphService,
    LLMProtocol,
    ProcessingError,
)


@pytest.fixture
def mock_env_key() -> Any:
    """Fixture to safely inject a valid encryption key for tests."""
    return mock.patch.dict(
        os.environ, {"MATOME_ENCRYPTION_KEY": Fernet.generate_key().decode("utf-8")}
    )


class MockLLMProtocol(LLMProtocol):
    def invoke(self, prompt: str, timeout: int = 30, retries: int = 3, **kwargs: Any) -> str:
        return "mock"


class MockDocumentProcessingService(DocumentProcessingService):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        pass

    def process(self, state: GraphState) -> GraphState:
        return state

    def process_stream(self, file_path: str, chunk_size: int = 1000) -> Any:
        yield from []


class MockKnowledgeGraphService(KnowledgeGraphService):
    def generate_raptor_tree(self, state: GraphState) -> GraphState:
        return state

    def generate_raptor_tree_batch(self, state: GraphState, batch_size: int = 100) -> GraphState:
        return state

    def pivot_kj(self, state: GraphState) -> GraphState:
        return state


class MockActiveLearningService(ActiveLearningService):
    def evaluate_answer(self, node: Any, answer: str) -> bool:
        return True

    def generate_question(self, node: Any, difficulty: str = "normal") -> str:
        return ""

    def track_progress(self, user_id: str, node_id: str, success: bool) -> None:
        pass

    def get_feedback(self, node: Any, answer: str) -> str:
        return ""


def llm_factory(*args: Any, **kwargs: Any) -> Any:
    return MockLLMProtocol()


def mock_resolve_class_side_effect(path: str) -> Any:
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


def test_init_container(mock_env_key: Any) -> None:
    with mock_env_key, mock.patch("src.container.resolve_class") as mock_resolve:
        mock_resolve.side_effect = mock_resolve_class_side_effect

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


@pytest.fixture
def cwd_tmp_path(tmp_path: Path) -> Any:
    """Creates a temporary directory strictly within cwd for path traversal tests."""
    # This ensures tests pass the strict is_relative_to(Path.cwd()) check
    test_dir = Path.cwd() / "test_temp_dir"
    test_dir.mkdir(exist_ok=True)
    yield test_dir
    # Cleanup
    import shutil

    shutil.rmtree(test_dir, ignore_errors=True)


def test_document_processing_workflow(cwd_tmp_path: Path) -> None:
    """Cycle 3: Tests the full LangGraph state transition and semantic chunking structure."""

    # Mock LLM Gateway to simulate embedding
    from src.interfaces import LLMProtocol

    class MockGateway(LLMProtocol):
        def invoke(self, prompt: str, timeout: int = 30, retries: int = 3, **kwargs: Any) -> str:
            return "embedding simulated"

    service = DocumentProcessingServiceImpl(llm_gateway=MockGateway())

    # Create valid text file with structured content
    test_file = cwd_tmp_path / "valid_doc.txt"
    content = "Sentence one is here. \n\n Sentence two is here. \n\n Microsoft is tech."
    test_file.write_text(content, encoding="utf-8")

    state = GraphState(file_path=str(test_file))

    # Process
    final_state = service.process(state)

    assert final_state.raw_text == content
    assert final_state.cleaned_text is not None
    assert "Sentence one is here." in final_state.cleaned_text
    assert final_state.embedded_chunks is True

    # Check structure instead of specific regex capture which can be brittle
    assert len(final_state.chunks) > 0
    assert final_state.chunks[0].metadata.source_document == str(test_file)
    assert isinstance(final_state.chunks[0].metadata.entities_extracted, list)


def test_document_processing_path_traversal() -> None:
    """Cycle 3: Verifies path traversal attacks raise ValueErrors immediately."""
    service = DocumentProcessingServiceImpl()

    malicious_path = "../../../../etc/passwd"
    state = GraphState(file_path=malicious_path)

    with pytest.raises(ValueError, match="Path traversal detected"):
        service.parse(state)


def test_document_processing_redos(cwd_tmp_path: Path) -> None:
    """Cycle 3: Verifies that semantic chunking bounds execution time (ReDoS mitigation)."""
    service = DocumentProcessingServiceImpl()

    test_file = cwd_tmp_path / "redos.txt"
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


def test_document_processing_empty_file(cwd_tmp_path: Path) -> None:
    """Cycle 3: Asserts empty file produces empty chunks but completes gracefully."""
    service = DocumentProcessingServiceImpl()

    test_file = cwd_tmp_path / "empty.txt"
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


def test_document_processing_stream(cwd_tmp_path: Path) -> None:
    """Cycle 3: Tests process_stream method."""
    service = DocumentProcessingServiceImpl()

    test_file = cwd_tmp_path / "stream_doc.txt"
    content = "Hello stream. World is good."
    test_file.write_text(content, encoding="utf-8")

    chunks = list(service.process_stream(str(test_file)))
    assert len(chunks) > 0
    assert "Hello stream." in chunks[0].text or "World is good." in chunks[-1].text
