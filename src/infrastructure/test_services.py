import logging
import re
from pathlib import Path

logger = logging.getLogger(__name__)


class FileProcessingError(Exception):
    """Custom exception for file processing errors."""


class FileProcessingService:
    """Service for securely processing local files."""

    def __init__(self) -> None:
        self._upload_dir = Path("testfiles").resolve(strict=False)
        self._upload_dir.mkdir(parents=True, exist_ok=True)
        self._max_file_size = 50 * 1024 * 1024  # 50 MB

    def read_file(self, filename: str) -> str:
        """Securely reads a file from the upload directory."""
        if not re.match(r"^[\w\-. ]+$", filename):
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
        try:
            with resolved_path.open(encoding="utf-8") as f:
                while chunk := f.read(1024 * 1024):  # 1MB chunks
                    content_chunks.append(chunk)
                    if len(content_chunks) * 1024 * 1024 > self._max_file_size:
                        msg = "File size exceeds memory limits during read."
                        raise FileProcessingError(msg)
        except OSError as e:
            logger.exception("Error reading file.")
            msg = "File processing failed."
            raise FileProcessingError(msg) from e

        return "".join(content_chunks)
