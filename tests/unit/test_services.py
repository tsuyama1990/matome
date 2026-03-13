from pathlib import Path

import pytest

from src.config.settings import AppConfig
from src.infrastructure.test_services import FileProcessingError, FileProcessingService


def test_file_processing_service_valid_file(tmp_path: Path) -> None:
    config = AppConfig(
        database_uri_encrypted="encrypted", upload_dir=str(tmp_path), max_file_size=1024 * 1024
    )
    service = FileProcessingService(config)

    test_file = tmp_path / "valid_file.txt"
    test_file.write_text("Hello, world!", encoding="utf-8")

    content = service.read_file("valid_file.txt")
    assert content == "Hello, world!"


def test_file_processing_service_invalid_path(tmp_path: Path) -> None:
    config = AppConfig(database_uri_encrypted="encrypted", upload_dir=str(tmp_path))
    service = FileProcessingService(config)
    with pytest.raises(ValueError, match="Invalid file path."):
        service.read_file("../../../etc/passwd")


def test_file_processing_service_file_not_found(tmp_path: Path) -> None:
    config = AppConfig(database_uri_encrypted="encrypted", upload_dir=str(tmp_path))
    service = FileProcessingService(config)

    with pytest.raises(FileProcessingError, match="File processing failed."):
        service.read_file("nonexistent.txt")


def test_file_processing_service_file_too_large(tmp_path: Path) -> None:
    config = AppConfig(database_uri_encrypted="encrypted", upload_dir=str(tmp_path), max_file_size=10)
    service = FileProcessingService(config)

    test_file = tmp_path / "large_file.txt"
    test_file.write_text("This file is way too large for the 10 byte limit.", encoding="utf-8")

    with pytest.raises(FileProcessingError, match="File size exceeds the allowed limit."):
        service.read_file("large_file.txt")
