import logging
import re
from pathlib import Path
from typing import Any

import httpx

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
        import hashlib
        import unicodedata

        if not filename or not isinstance(filename, str):
            msg = "Invalid file path structure."
            raise ValueError(msg)

        if "\0" in filename:
            msg = "Invalid file path structure: null bytes not allowed."
            raise ValueError(msg)

        # Pre-normalization checks to prevent obvious injections
        if "/" in filename or "\\" in filename or ".." in filename:
            msg = "Filename contains directory traversal patterns"
            raise ValueError(msg)

        normalized_filename = unicodedata.normalize("NFKD", filename)
        if len(normalized_filename.encode("utf-8")) > 255:
            msg = "Filename exceeds maximum allowed byte length"
            raise ValueError(msg)

        # Generate a strict, safe cryptographic mapping name avoiding ALL traversal possibilities
        file_hash = hashlib.sha256(normalized_filename.encode("utf-8")).hexdigest()

        # We only retain the alphanumeric extension if it is explicitly whitelisted
        # (Since we validate MIME downstream anyway, forcing a static .bin extension or .txt is safest,
        # but to keep testing simpler we just return the hex hash)
        return f"{file_hash}.safe"

    def _read_file_content(self, resolved_path: Path) -> str:
        """Internal method to perform the actual chunked read operation."""

        content_chunks = []
        total_size = 0
        try:
            if resolved_path.stat().st_size > self._max_file_size:
                msg = "File size exceeds the allowed limit."
                raise FileProcessingError(msg)

            # Open with strict encoding to catch malformed characters
            with resolved_path.open(encoding="utf-8", errors="strict") as f:
                # Keep streaming limits bounded per read to respect memory limits and prevent TOCTOU.
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


class PlainTextParser:
    """Minimal text parser for testing."""

    async def parse(self, file_content: bytes, filename: str) -> str:
        """Parses the text from the bytes."""
        return file_content.decode("utf-8", errors="replace")


class DummyEmbeddingService:
    """Dummy embedding service for testing."""

    def __init__(self, dimension: int = 384) -> None:
        self.dimension = dimension

    async def embed_text(self, text: str) -> list[float]:
        """Returns a dummy embedding of the configured dimension."""
        # Using 0.1 for deterministic tests
        return [0.1] * self.dimension


class SafeTestLLMService:
    """Minimal test implementation of LLMProtocol without mocking."""

    def __init__(self, raise_error: bool = False) -> None:
        self.raise_error = raise_error
        self._call_count = 0

    def get_call_count(self) -> int:
        return self._call_count

    async def generate(self, prompt: str) -> str:
        self._call_count += 1
        if self.raise_error:
            msg = "LLM connection failed"
            raise ValueError(msg)
        return "Test Summary or Question."

    async def generate_text(self, prompt: str, model: str) -> str:
        self._call_count += 1
        if self.raise_error:
            msg = "LLM connection failed"
            raise ValueError(msg)
        return "Test Summary or Question."


class DummyLLMService:
    """Dummy test implementation of LLMProtocol."""

    def __init__(self, raise_error: bool = False) -> None:
        self.raise_error = raise_error
        self._call_count = 0

    def get_call_count(self) -> int:
        return self._call_count

    async def generate(self, prompt: str) -> str:
        self._call_count += 1
        if self.raise_error:
            msg = "LLM connection failed"
            raise ValueError(msg)
        return "Test Summary or Question."

    async def generate_text(self, prompt: str, model: str) -> str:
        self._call_count += 1
        if self.raise_error:
            msg = "LLM connection failed"
            raise ValueError(msg)
        return "Test Summary or Question."


class SafeTestDocumentRepository:
    """Minimal test implementation of DocumentRepositoryProtocol without mocking."""

    def __init__(self, doc: Any = None, raise_error: bool = False) -> None:
        self.doc = doc
        self.raise_error = raise_error

    def get_document_by_id(self, document_id: str) -> Any:
        if self.raise_error:
            msg = "DB connection failed"
            raise ValueError(msg)
        if not self.doc:
            msg = "Not found"
            raise ValueError(msg)
        return self.doc


class MockHTTPTransport(httpx.AsyncBaseTransport):
    """A clean, protocol-compliant mock transport avoiding direct class-level httpx instantiation state."""

    def __init__(self) -> None:
        self.responses: list[Any] = []
        self.call_count = 0
        self.requests: list[Any] = []

    def add_response(
        self,
        status_code: int = 200,
        json_data: dict[str, Any] | None = None,
        exc: Exception | None = None,
    ) -> None:
        if exc is not None:
            if not isinstance(exc, Exception):
                msg = "exc must be an Exception"
                raise ValueError(msg)

            allowed_exceptions = (
                httpx.ConnectError,
                httpx.TimeoutException,
                httpx.RequestError,
                httpx.HTTPStatusError,
            )
            if not isinstance(exc, allowed_exceptions):
                msg = "exc must be a valid httpx exception"
                raise ValueError(msg)
            self.responses.append(exc)
        else:
            self.responses.append((status_code, json_data))

    async def aclose(self) -> None:
        pass

    async def handle_async_request(self, request: Any) -> Any:
        self.call_count += 1
        self.requests.append(request)

        if not self.responses:
            return httpx.Response(
                status_code=200,
                json={"choices": [{"message": {"content": "Mock fallback success"}}]},
                request=request,
            )

        resp = self.responses.pop(0)
        if isinstance(resp, Exception):
            raise resp

        status_code, json_data = resp
        import json

        body = json.dumps(json_data).encode("utf-8") if json_data else b""
        stream = httpx.ByteStream(body)
        return httpx.Response(
            status_code=status_code,
            headers=[(b"content-type", b"application/json")],
            stream=stream,
            request=request,
        )


# For backward compatibility with tests using the old name
MockHttpxTransport = MockHTTPTransport


class SafeTestHTTPTransport:
    """Minimal test implementation of httpx.AsyncBaseTransport without mocking."""

    def __init__(
        self,
        response_data: dict[str, Any],
        status_code: int = 200,
        raise_exception: Exception | None = None,
    ) -> None:
        if raise_exception is not None and not isinstance(raise_exception, Exception):
            msg = "raise_exception must be an Exception"
            raise ValueError(msg)

        self.response_data = response_data
        self.status_code = status_code
        self.raise_exception = raise_exception

    async def aclose(self) -> None:
        pass

    async def handle_async_request(self, request: Any) -> Any:
        import json

        if self.raise_exception:
            raise self.raise_exception

        body = json.dumps(self.response_data).encode("utf-8")
        stream = httpx.ByteStream(body)
        return httpx.Response(
            status_code=self.status_code,
            headers=[(b"content-type", b"application/json")],
            stream=stream,
            request=request,
        )
