from pathlib import Path

import pytest

from src.document import DocumentProcessor
from src.domain_models.config import PipelineConfig


def test_document_processor_path_traversal() -> None:
    processor = DocumentProcessor()

    with pytest.raises(ValueError, match="Path traversal attempt blocked."):
        list(processor.process_stream("../../etc/passwd"))

    with pytest.raises(ValueError, match="Path traversal attempt blocked."):
        list(processor.process_stream("/etc/passwd"))


def test_document_processor_file_not_found() -> None:
    processor = DocumentProcessor()

    with pytest.raises(ValueError, match="File not found: "):
        list(processor.process_stream("nonexistent_file.txt"))


def test_document_processor_max_size_limit(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    config = PipelineConfig(max_chunk_scan_size=10)
    processor = DocumentProcessor(config=config)

    test_file = tmp_path / "large_file.txt"
    test_file.write_text("This file is way larger than ten bytes.")

    monkeypatch.setattr(Path, "cwd", lambda: tmp_path)

    with pytest.raises(ValueError, match="File size exceeds maximum allowed size"):
        list(processor.process_stream(str(test_file)))


def test_document_processor_successful_stream(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    config = PipelineConfig()
    processor = DocumentProcessor(config=config)

    test_file = tmp_path / "valid_file.txt"
    test_file.write_text("chunk 1 text. chunk 2 text.", encoding="utf-8")

    monkeypatch.setattr(Path, "cwd", lambda: tmp_path)

    chunks = list(processor.process_stream(str(test_file), chunk_size=10))

    assert len(chunks) > 0
    assert chunks[0].text.startswith("chunk 1")
    assert chunks[0].metadata.source_document == str(test_file.resolve(strict=True))
