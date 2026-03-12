import logging
import re
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

        try:
            resolved_path = Path(file_path_str).resolve(strict=True)
        except FileNotFoundError as e:
            msg = f"Path {file_path_str} does not exist"
            raise ValueError(msg) from e

        # Strict CWD check
        allowed_dir = Path(str(self.config.allowed_input_dir)).resolve() if getattr(self.config, 'allowed_input_dir', None) is not None else Path.cwd()
        if not resolved_path.is_relative_to(allowed_dir):
            msg = f"Path {resolved_path} is outside the allowed directory {allowed_dir}"
            raise ValueError(msg)

        try:
            stat_result = resolved_path.stat()
            import stat
            if not stat.S_ISREG(stat_result.st_mode):
                msg = f"Path {resolved_path} does not point to a regular file"
                raise ValueError(msg)
            file_size = stat_result.st_size
        except FileNotFoundError as e:
            msg = f"File {resolved_path} was removed or does not exist"
            raise ProcessingError(msg) from e

        if file_size > self.config.max_file_size:
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
        # Find Capitalized words strictly bounded to 15 lowercase chars to prevent ReDoS.
        pattern = re.compile(r"\b[A-Z][a-z]{1,15}\b")
        return [match.group(0) for match in pattern.finditer(text)]

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
        """Streams a file processing to reduce memory overhead by processing byte chunks incrementally."""
        import codecs
        resolved_path = self._secure_resolve_path(file_path)

        decoder = codecs.getincrementaldecoder('utf-8')(errors='strict')
        text_buffer = ""

        with resolved_path.open("rb") as f:
            while True:
                # Use chunk_size as byte size limit instead of line counts
                binary_chunk = f.read(chunk_size * 1024)
                if not binary_chunk:
                    break

                try:
                    decoded_text = decoder.decode(binary_chunk)
                except UnicodeDecodeError as e:
                    msg = "Failed to incrementally decode file as UTF-8"
                    raise ProcessingError(msg) from e

                text_buffer += decoded_text

                # We need semantic breaks (paragraphs) to chunk safely
                while "\n\n" in text_buffer:
                    paragraph, text_buffer = text_buffer.split("\n\n", 1)
                    normalized_text = self._normalize_text(paragraph)
                    if normalized_text:
                        chunks = self._chunk_text(normalized_text)
                        yield from chunks

        # Process remaining buffer
        try:
            final_text = decoder.decode(b"", final=True)
            text_buffer += final_text
        except UnicodeDecodeError as e:
            msg = "Failed to incrementally decode file as UTF-8 at EOF"
            raise ProcessingError(msg) from e

        if text_buffer:
            normalized_text = self._normalize_text(text_buffer)
            if normalized_text:
                chunks = self._chunk_text(normalized_text)
                yield from chunks
