from collections.abc import Iterator
from pathlib import Path

from src.domain_models import SemanticChunk
from src.interfaces import DocumentProcessingService, ProcessingError


class DefaultDocumentProcessingService(DocumentProcessingService):
    """Production implementation of the DocumentProcessingService."""

    def process_stream(self, file_path: str, chunk_size: int = 1000) -> Iterator[SemanticChunk]:
        """Streams semantic chunks securely."""
        try:
            # We enforce basic file reading logic securely via pathlib.
            p = Path(file_path).resolve(strict=True)
            with p.open("r", encoding="utf-8", errors="strict") as f:
                content = f.read(chunk_size)
                index = 0
                while content:
                    if content.strip():
                        yield SemanticChunk(id=f"chunk_{index}", text=content)
                        index += 1
                    content = f.read(chunk_size)
        except UnicodeDecodeError as e:
            msg = f"Invalid file encoding: {e}"
            raise ProcessingError(msg) from e
        except OSError as e:
            msg = f"Failed to securely read file {file_path}: {e}"
            raise ProcessingError(msg) from e

    def process(self, file_path: str) -> list[SemanticChunk]:
        """Processes a file entirely and returns all chunks."""
        return list(self.process_stream(file_path))
