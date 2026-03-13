from pathlib import Path

import pytest

from src.infrastructure.test_services import FileProcessingError, FileProcessingService


def test_file_processing_service_valid_file(tmp_path: Path) -> None:
    service = FileProcessingService()
    service._upload_dir = tmp_path
    service._max_file_size = 1024 * 1024

    test_file = tmp_path / "valid_file.txt"
    test_file.write_text("Hello, world!", encoding="utf-8")

    content = service.read_file("valid_file.txt")
    assert content == "Hello, world!"

def test_file_processing_service_invalid_path() -> None:
    service = FileProcessingService()
    with pytest.raises(ValueError, match="Invalid file path."):
        service.read_file("../../../etc/passwd")

def test_file_processing_service_file_not_found(tmp_path: Path) -> None:
    service = FileProcessingService()
    service._upload_dir = tmp_path

    with pytest.raises(FileProcessingError, match="File processing failed."):
        service.read_file("nonexistent.txt")

def test_file_processing_service_file_too_large(tmp_path: Path) -> None:
    service = FileProcessingService()
    service._upload_dir = tmp_path
    service._max_file_size = 10  # 10 bytes

    test_file = tmp_path / "large_file.txt"
    test_file.write_text("This file is way too large for the 10 byte limit.", encoding="utf-8")

    with pytest.raises(FileProcessingError, match="File size exceeds the allowed limit."):
        service.read_file("large_file.txt")
