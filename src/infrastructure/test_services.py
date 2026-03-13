import logging
import re
from pathlib import Path

from src.config.settings import AppConfig

logger = logging.getLogger(__name__)


class FileProcessingError(Exception):
    """Custom exception for file processing errors."""


class FileProcessingService:
    """Service for securely processing local files."""

    def __init__(self, config: AppConfig) -> None:
        self._upload_dir = Path(config.upload_dir).resolve(strict=False)
        self._upload_dir.mkdir(parents=True, exist_ok=True)
        self._max_file_size = config.max_file_size

    def read_file(self, filename: str) -> str:
        """Securely reads a file from the upload directory."""
        # Strictly prevent path traversal characters and limit to safe alphanumeric characters
        if not re.match(r"^[a-zA-Z0-9_\-\.]+$", filename):
            msg = "Invalid file path."
            raise ValueError(msg)

        try:
            resolved_path = self._upload_dir.joinpath(filename).resolve(strict=True)
            if not resolved_path.is_relative_to(self._upload_dir):
                msg = "Invalid file path."
                raise ValueError(msg)

            if resolved_path.stat().st_size > self._max_file_size:
                msg = "File size exceeds the allowed limit."
                raise FileProcessingError(msg)
        except FileNotFoundError as e:
            logger.exception("File not found.")
            msg = "File processing failed."
            raise FileProcessingError(msg) from e
        except OSError as e:
            logger.exception("OS error during file resolution.")
            msg = "File processing failed."
            raise FileProcessingError(msg) from e

        content_chunks = []
        total_size = 0
        try:
            with resolved_path.open(encoding="utf-8") as f:
                while chunk := f.read(1024 * 1024):  # 1MB chunks
                    total_size += len(chunk.encode("utf-8"))
                    if total_size > self._max_file_size:
                        msg = "File size exceeds memory limits during read."
                        raise FileProcessingError(msg)
                    content_chunks.append(chunk)
        except OSError as e:
            logger.exception("Error reading file.")
            msg = "File processing failed."
            raise FileProcessingError(msg) from e

        return "".join(content_chunks)
