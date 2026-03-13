import re
import uuid
from pathlib import Path

from src.config.settings import AppConfig
from src.domain_models.document import ChunkMetadata, SemanticChunk
from src.domain_models.exceptions import ProcessingError
from src.interfaces.dependencies import ChunkingProtocol, DocumentParserProtocol


class SimpleParsingService(DocumentParserProtocol):
    """A deterministic parsing service."""

    def __init__(self, config: AppConfig) -> None:
        self._upload_dir = Path(config.upload_dir)

    def parse(self, filename: str) -> str:
        """Parses a file from the configured upload directory."""
        try:
            # Secure path resolution to prevent path traversal
            resolved_path = self._upload_dir.joinpath(filename).resolve(strict=True)
            if not resolved_path.is_relative_to(self._upload_dir.resolve()):
                msg = "Path traversal blocked."
                raise ValueError(msg)  # noqa: TRY301

            with resolved_path.open(encoding="utf-8") as f:
                return f.read()
        except FileNotFoundError as e:
            msg = f"File not found: {filename}"
            raise ProcessingError(msg) from e
        except Exception as e:
            msg = f"Error parsing file: {e}"
            raise ProcessingError(msg) from e


class SimpleChunkingService(ChunkingProtocol):
    """A deterministic chunking service using bounded regex."""

    def chunk_text(self, text: str, source_file: str) -> list[SemanticChunk]:
        """Splits text into chunks deterministically."""
        if not text:
            msg = "Cannot chunk empty text."
            raise ProcessingError(msg)

        chunks = []
        # Split using bounded length to avoid unbounded quantifiers.
        sentences = re.split(r"(?<=[.!?])\s{1,5}(?=[A-Z])", text)
        for i, sentence in enumerate(sentences):
            metadata = ChunkMetadata(source_file=source_file, page_number=i + 1)
            chunk = SemanticChunk(
                id=uuid.uuid4(),
                content=sentence.strip(),
                metadata=metadata,
            )
            chunks.append(chunk)

        return chunks
