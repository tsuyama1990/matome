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

    def _validate_filename(self, filename: str) -> str:
        import unicodedata

        if "\0" in filename:
            msg = "Invalid file path structure"
            raise ValueError(msg)

        if len(filename) > 255:
            msg = "Filename exceeds maximum allowed length"
            raise ValueError(msg)

        normalized_filename = unicodedata.normalize("NFKD", filename)

        # Block all non-alphanumeric characters except safe basic punctuation, allow unicode letters
        if not re.match(r"^[\w\-\.]+$", normalized_filename, re.UNICODE):
            msg = "Filename contains invalid characters"
            raise ValueError(msg)

        return normalized_filename

    def _read_file_content(self, resolved_path: Path) -> str:
        """Internal method to perform the actual chunked read operation."""
        import os

        content_chunks = []
        total_size = 0
        try:
            # Open with strict encoding to catch malformed characters
            with resolved_path.open(encoding="utf-8", errors="strict") as f:
                # TOCTOU mitigation: Check size on the open file descriptor.
                fd_size = os.fstat(f.fileno()).st_size
                if fd_size > self._max_file_size:
                    msg = "File size exceeds the allowed limit"
                    raise FileProcessingError(msg)

                # Keep streaming limits bounded per read to respect memory limits.
                while chunk := f.read(1024 * 1024):  # 1MB chunks
                    chunk_byte_len = len(chunk.encode("utf-8", errors="strict"))

                    # Track exact memory consumption against limit BEFORE appending
                    if total_size + chunk_byte_len > self._max_file_size:
                        msg = "File size exceeds memory limits during read."
                        raise FileProcessingError(msg)

                    total_size += chunk_byte_len
                    content_chunks.append(chunk)
        except UnicodeDecodeError as e:
            logger.exception("Encoding error during file read.")
            msg = "File contains invalid UTF-8 encoding."
            raise FileProcessingError(msg) from e
        except OSError as e:
            logger.exception("Error reading file.")
            msg = "File processing failed."
            raise FileProcessingError(msg) from e

        return "".join(content_chunks)

    def read_file(self, filename: str) -> str:
        """Securely reads a file from the upload directory with portable timeout protection."""
        normalized_filename = self._validate_filename(filename)

        try:
            # We explicitly prevent path traversal using strict resolution and
            # checking if the target remains in the designated upload dir.
            resolved_path = self._upload_dir.joinpath(normalized_filename).resolve(strict=True)
            if not resolved_path.is_relative_to(self._upload_dir):
                msg = "Resolved path is outside upload directory"
                raise ValueError(msg)
        except FileNotFoundError as e:
            logger.exception("File not found.")
            msg = "File not found"
            raise FileProcessingError(msg) from e
        except OSError as e:
            logger.exception("OS error during file resolution.")
            msg = "File resolution failed due to OS error"
            raise FileProcessingError(msg) from e

        import concurrent.futures

        # Implement a portable, cross-platform timeout using ThreadPoolExecutor
        # to prevent DoS via extremely slow/large file reads.
        try:
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(self._read_file_content, resolved_path)
                return future.result(timeout=30.0)
        except concurrent.futures.TimeoutError as e:
            logger.exception("File reading timed out.")
            msg = "File processing timed out."
            raise FileProcessingError(msg) from e


class SimpleParsingService:
    """A minimal parsing service meant purely for tests."""

    def parse_document(self, content: str) -> list[str]:
        """Splits the content roughly into sentences/chunks."""
        if not content:
            return []

        # very basic naive splitting for test simplicity
        return [c.strip() for c in re.split(r"(?<=[.!?])\s+", content) if c.strip()]
