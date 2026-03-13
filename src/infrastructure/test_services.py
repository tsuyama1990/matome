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
        # Explicitly deny null bytes to prevent C-style injection attacks.
        if "\0" in filename:
            msg = "Invalid file path structure"
            raise ValueError(msg)

        try:
            # We explicitly prevent path traversal using strict resolution and
            # checking if the target remains in the designated upload dir.
            resolved_path = self._upload_dir.joinpath(filename).resolve(strict=True)
            if not resolved_path.is_relative_to(self._upload_dir):
                msg = "Resolved path is outside upload directory"
                raise ValueError(msg)

            file_size = resolved_path.stat().st_size
            if file_size > self._max_file_size:
                msg = "File size exceeds the allowed limit"
                raise FileProcessingError(msg)
        except FileNotFoundError as e:
            logger.exception("File not found.")
            msg = "File not found"
            raise FileProcessingError(msg) from e
        except OSError as e:
            logger.exception("OS error during file resolution.")
            msg = "File resolution failed due to OS error"
            raise FileProcessingError(msg) from e

        content_chunks = []
        total_size = 0
        try:
            with resolved_path.open(encoding="utf-8") as f:
                # The file size is already strictly checked above against limits
                # (via st_size). However, we continue to incrementally chunk to
                # keep streaming limits bounded per read to respect memory limits.
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


class SimpleParsingService:
    """A minimal parsing service meant purely for tests."""

    def parse_document(self, content: str) -> list[str]:
        """Splits the content roughly into sentences/chunks."""
        if not content:
            return []

        # very basic naive splitting for test simplicity
        return [c.strip() for c in re.split(r"(?<=[.!?])\s+", content) if c.strip()]
