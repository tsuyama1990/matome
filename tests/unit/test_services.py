from pathlib import Path

import pytest

from src.config.settings import AppConfig
from src.infrastructure.test_services import (
    FileProcessingError,
    FileProcessingService,
    SimpleParsingService,
)


def test_file_processing_service_valid_file(tmp_path: Path) -> None:
    config = AppConfig(upload_dir=str(tmp_path), max_file_size=1024 * 1024)
    service = FileProcessingService(config)

    test_file = tmp_path / "valid_file.txt"
    test_file.write_text("Hello, world!", encoding="utf-8")

    content = service.read_file("valid_file.txt")
    assert content == "Hello, world!"


def test_file_processing_service_invalid_path(tmp_path: Path) -> None:
    config = AppConfig(upload_dir=str(tmp_path))
    service = FileProcessingService(config)

    with pytest.raises(ValueError, match="Filename contains directory traversal patterns"):
        service.read_file("../../../etc/passwd")

    # Also test null byte injection
    with pytest.raises(ValueError, match="Invalid file path structure"):
        service.read_file("file.txt\0.pdf")

    # Test extreme filename length
    long_filename = "a" * 260 + ".txt"
    with pytest.raises(ValueError, match="Filename exceeds maximum allowed length"):
        service.read_file(long_filename)


def test_file_processing_service_valid_unicode_filename(tmp_path: Path) -> None:
    config = AppConfig(upload_dir=str(tmp_path), max_file_size=1024 * 1024)
    service = FileProcessingService(config)

    filename = "テスト_ファイル-1.txt"
    test_file = tmp_path / filename
    test_file.write_text("Unicode content", encoding="utf-8")

    content = service.read_file(filename)
    assert content == "Unicode content"


def test_file_processing_service_file_not_found(tmp_path: Path) -> None:
    config = AppConfig(upload_dir=str(tmp_path))
    service = FileProcessingService(config)

    with pytest.raises(FileProcessingError, match="File not found"):
        service.read_file("nonexistent.txt")


def test_file_processing_service_file_too_large(tmp_path: Path) -> None:
    config = AppConfig(upload_dir=str(tmp_path), max_file_size=10)
    service = FileProcessingService(config)

    test_file = tmp_path / "large_file.txt"
    test_file.write_text("This file is way too large for the 10 byte limit.", encoding="utf-8")

    with pytest.raises(FileProcessingError, match="File size exceeds memory limits during read"):
        service.read_file("large_file.txt")


def test_simple_parsing_service() -> None:
    service = SimpleParsingService()
    content = "Hello there. How are you! I am fine."
    chunks = service.parse_document(content)
    assert chunks == ["Hello there.", "How are you!", "I am fine."]

    empty_chunks = service.parse_document("")
    assert empty_chunks == []
