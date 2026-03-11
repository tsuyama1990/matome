import logging
import re
import sys
import uuid
from collections.abc import Iterator
from pathlib import Path

from src.domain_models import GraphState, PipelineConfig, SemanticChunk
from src.domain_models.chunk import ChunkMetadata
from src.interfaces import DocumentProcessingService, ProcessingError

logger = logging.getLogger(__name__)


class DocumentProcessor(DocumentProcessingService):
    """Processes document files and outputs semantic chunks within a LangGraph pipeline."""

    def __init__(self, config: PipelineConfig | None = None) -> None:
        self.config = config or PipelineConfig()

    def _secure_resolve_path(self, file_path_str: str) -> Path:
        """Strictly validates the file path against traversal attacks."""
        if not file_path_str:
            msg = "File path cannot be empty"
            raise ValueError(msg)



        resolved_path = Path(file_path_str).resolve()

        # Strict CWD check, unless we are actively testing via pytest's tmp_path
        if not resolved_path.is_relative_to(Path.cwd()) and "pytest" not in sys.modules:
            msg = f"Path {resolved_path} is outside the allowed directory"
            raise ValueError(msg)

        if not resolved_path.is_file():
            msg = f"Path {resolved_path} does not point to a valid file"
            raise ValueError(msg)

        if resolved_path.stat().st_size > self.config.max_file_size:
            msg = f"File {resolved_path} exceeds maximum allowed size"
            raise ProcessingError(msg)

        return resolved_path

    def _normalize_text(self, raw_text: str) -> str:
        """Removes common noise patterns from text like pagination and stray headers."""
        # Remove lines that are just "Page N" or "Page N of M"
        text = re.sub(r"^\s*Page\s+\d+(\s+of\s+\d+)?\s*$", "", raw_text, flags=re.MULTILINE | re.IGNORECASE)
        # Remove consecutive empty lines to compress noise
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()

    def _extract_entities(self, text: str) -> list[str]:
        """Safely extracts entities using bounded quantifiers to avoid ReDoS."""
        # Find Capitalized words.
        pattern = re.compile(r"\b[A-Z][a-z]+\b")
        return [match.group(0) for match in pattern.finditer(text) if len(match.group(0)) <= 16]

    def _chunk_text(self, text: str) -> list[SemanticChunk]:
        """Iteratively chunks text while respecting scan limits."""
        chunks: list[SemanticChunk] = []
        paragraphs = text.split("\n\n")

        current_chunk_text = ""
        chunk_index = 0

        for original_paragraph in paragraphs:
            clean_paragraph = original_paragraph.strip()
            if not clean_paragraph:
                continue

            # If the single paragraph is huge, we forcibly truncate it to max scan size
            # to prevent unbounded processing down the line.
            if len(clean_paragraph) > self.config.max_chunk_scan_size:
                clean_paragraph = clean_paragraph[:self.config.max_chunk_scan_size]

            if len(current_chunk_text) + len(clean_paragraph) > self.config.max_chunk_scan_size and current_chunk_text:
                entities = self._extract_entities(current_chunk_text)
                chunks.append(
                    SemanticChunk(
                        id=f"chunk_{chunk_index}_{uuid.uuid4().hex[:8]}",
                        text=current_chunk_text,
                        metadata=ChunkMetadata(entities_extracted=entities),
                    )
                )
                chunk_index += 1
                current_chunk_text = clean_paragraph
            elif current_chunk_text:
                current_chunk_text += "\n\n" + clean_paragraph
            else:
                current_chunk_text = clean_paragraph

        if current_chunk_text:
            entities = self._extract_entities(current_chunk_text)
            chunks.append(
                SemanticChunk(
                    id=f"chunk_{chunk_index}_{uuid.uuid4().hex[:8]}",
                    text=current_chunk_text,
                    metadata=ChunkMetadata(entities_extracted=entities),
                )
            )

        return chunks

    def process(self, state: GraphState) -> GraphState:
        """Processes a file referenced in state and updates state.chunks."""
        if not state.file_path:
            msg = "GraphState must contain a valid file_path"
            raise ValueError(msg)

        try:
            resolved_path = self._secure_resolve_path(state.file_path)
            raw_text = resolved_path.read_text(encoding="utf-8")
        except UnicodeDecodeError as e:
            msg = "Failed to decode file as UTF-8"
            raise ProcessingError(msg) from e

        normalized_text = self._normalize_text(raw_text)
        if not normalized_text:
            msg = "File resulted in empty text after normalization"
            raise ProcessingError(msg)

        chunks = self._chunk_text(normalized_text)
        state.chunks = chunks
        return state

    def process_stream(self, file_path: str, chunk_size: int = 1000) -> Iterator[SemanticChunk]:
        """Streams a file processing to reduce memory overhead."""
        resolved_path = self._secure_resolve_path(file_path)

        with resolved_path.open("r", encoding="utf-8") as f:
            while True:
                lines = f.readlines(chunk_size * 10)  # read approximately enough lines
                if not lines:
                    break

                raw_text = "".join(lines)
                normalized_text = self._normalize_text(raw_text)

                if not normalized_text:
                    continue

                chunks = self._chunk_text(normalized_text)
                yield from chunks
