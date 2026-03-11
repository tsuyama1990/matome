import os
import sys
from pathlib import Path
from typing import Any
from unittest import mock

import pytest
from cryptography.fernet import Fernet

import main
from src.container import ProductionDIContainer
from src.document import DocumentProcessor
from src.domain_models import GraphState, PipelineConfig
from src.interfaces import ProcessingError


@pytest.fixture
def mock_env_key() -> Any:
    """Fixture to safely inject a valid encryption key for tests."""
    return mock.patch.dict(
        os.environ, {"MATOME_ENCRYPTION_KEY": Fernet.generate_key().decode("utf-8")}
    )

def test_init_container(mock_env_key: Any) -> None:
    with mock_env_key, mock.patch("src.container.resolve_class") as mock_resolve:
        from tests.unit.test_container import (
            MockActiveLearningService,
            MockDocumentProcessingService,
            MockKnowledgeGraphService,
            MockLLMProtocol,
        )

        def llm_factory(*args: Any, **kwargs: Any) -> Any:
            return MockLLMProtocol()

        def side_effect(path: str) -> Any:
            if "LLMProtocol" in path:
                return llm_factory
            if "DocumentProcessingService" in path:
                return MockDocumentProcessingService
            if "KnowledgeGraphService" in path:
                return MockKnowledgeGraphService
            if "ActiveLearningService" in path:
                return MockActiveLearningService
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
        mock_init.return_value = None
        result = main.main()
        assert result == 0
        captured = capsys.readouterr()
        assert "Hello from matome" in captured.out

def test_path_traversal_blocked() -> None:
    config = PipelineConfig(max_file_size=1024)
    processor = DocumentProcessor(config)

    state = GraphState(file_path="../etc/passwd")
    with pytest.raises(ValueError, match="Path traversal attempts are strictly forbidden"):
        processor.process(state)

    state2 = GraphState(file_path="/etc/passwd")
    original_pytest = sys.modules.pop('pytest', None)
    try:
        with pytest.raises(ValueError, match="Path .* is outside the allowed directory"):
            processor.process(state2)
    finally:
        if original_pytest:
            sys.modules['pytest'] = original_pytest

def test_file_size_limit_enforced(tmp_path: Path) -> None:
    config = PipelineConfig(max_file_size=10)
    processor = DocumentProcessor(config)

    large_file = tmp_path / "large.txt"
    large_file.write_text("This file is longer than 10 bytes.")

    state = GraphState(file_path=str(large_file))
    with pytest.raises(ProcessingError, match="exceeds maximum allowed size"):
        processor.process(state)

def test_text_normalization_removes_noise(tmp_path: Path) -> None:
    config = PipelineConfig(max_file_size=1024)
    processor = DocumentProcessor(config)

    noisy_text = (
        "Page 12\n"
        "Important header\n"
        "\n\n\n\n\n"
        "This is the actual content.\n"
        "Page 13 of 100\n"
    )
    test_file = tmp_path / "noise.txt"
    test_file.write_text(noisy_text)

    state = GraphState(file_path=str(test_file))
    final_state = processor.process(state)

    chunks = final_state.chunks
    assert len(chunks) == 1
    chunk_text = chunks[0].text
    assert "Page 12" not in chunk_text
    assert "Page 13 of 100" not in chunk_text
    assert "Important header" in chunk_text
    assert "This is the actual content." in chunk_text

def test_semantic_chunking_limits(tmp_path: Path) -> None:
    config = PipelineConfig(max_chunk_scan_size=50)
    processor = DocumentProcessor(config)

    long_para = "A" * 100
    test_file = tmp_path / "long.txt"
    test_file.write_text(long_para)

    state = GraphState(file_path=str(test_file))
    final_state = processor.process(state)

    chunks = final_state.chunks
    assert len(chunks) == 1
    assert len(chunks[0].text) == 50

def test_document_processing_workflow(tmp_path: Path) -> None:
    config = PipelineConfig(max_file_size=1024, max_chunk_scan_size=100)
    processor = DocumentProcessor(config)

    content = "This is a Test Document. It contains Multiple Entities. \n\nWe will see."
    test_file = tmp_path / "doc.txt"
    test_file.write_text(content)

    state = GraphState(file_path=str(test_file))
    state = processor.process(state)

    assert len(state.chunks) >= 1
    assert state.chunks[0].metadata is not None
    assert isinstance(state.chunks[0].metadata.entities_extracted, list)

    state = processor.embed(state)
    assert len(state.chunks) >= 1
