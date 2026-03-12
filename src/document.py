import uuid
from collections.abc import Iterator
from pathlib import Path

from src.domain_models.chunk import ChunkMetadata, SemanticChunk
from src.domain_models.config import PipelineConfig
from src.domain_models.state import GraphState
from src.interfaces import DocumentProcessingService, ProcessingError


class DocumentProcessor(DocumentProcessingService):
    """Implementation of the DocumentProcessingService."""

    def __init__(self, config: PipelineConfig | None = None) -> None:
        self.config = config or PipelineConfig()

    def process(self, state: GraphState) -> GraphState:
        """Processes a file referenced in state and updates state.chunks."""
        if not state.file_path:
            msg = "No file path provided in GraphState"
            raise ValueError(msg)

        chunks = list(self.process_stream(state.file_path, chunk_size=1000))

        import copy

        # We need to manually construct a new state using deepcopy to preserve true immutability
        return GraphState(
            file_path=state.file_path,
            chunks=copy.deepcopy(state.chunks) + chunks,
            tree=copy.deepcopy(state.tree),
            active_node_id=state.active_node_id,
            pivot_axis=state.pivot_axis,
            pivot_response=copy.deepcopy(state.pivot_response),
            error=state.error,
        )

    def _validate_path(self, file_path: str) -> Path:
        """Validates the file path for security and existance."""
        base_dir = Path.cwd()
        try:
            resolved_path = base_dir.joinpath(file_path).resolve(strict=True)
        except FileNotFoundError as e:
            msg = f"File not found: {file_path}"
            raise ValueError(msg) from e
        except OSError as e:
            msg = f"Invalid file path: {file_path}"
            raise ValueError(msg) from e

        if not resolved_path.is_relative_to(base_dir):
            msg = f"Path traversal attempt blocked. File must be within {base_dir}"
            raise ValueError(msg)
        return resolved_path

    def _validate_file_stats(self, resolved_path: Path) -> None:
        """Checks size limits and regular file type."""
        try:
            file_stat = resolved_path.stat()
        except FileNotFoundError as e:
            msg = f"File not found or deleted before stat: {resolved_path}"
            raise ValueError(msg) from e

        if not resolved_path.is_file():
            msg = f"Path is not a regular file: {resolved_path}"
            raise ValueError(msg)

        if file_stat.st_size > self.config.max_chunk_scan_size:
            msg = f"File size exceeds maximum allowed size of {self.config.max_chunk_scan_size} bytes"
            raise ValueError(msg)

    def process_stream(self, file_path: str, chunk_size: int = 1000) -> Iterator[SemanticChunk]:
        """Streams a file processing to reduce memory overhead."""
        resolved_path = self._validate_path(file_path)
        self._validate_file_stats(resolved_path)

        # Streaming bytes with incremental decoding
        import codecs

        try:
            decoder = codecs.getincrementaldecoder("utf-8")(errors="strict")
            with resolved_path.open("rb") as f:
                buffer = ""
                page_counter = 1
                while True:
                    # Read bytes in small chunks to avoid memory exhaustion
                    # Use a small byte size to simulate byte-level streaming as required
                    chunk = f.read(chunk_size)
                    if not chunk:
                        # Flush the decoder
                        text_chunk = decoder.decode(b"", final=True)
                        if text_chunk:
                            buffer += text_chunk
                        if buffer.strip():
                            yield self._create_chunk(buffer, str(resolved_path), page_counter)
                        break

                    # Decode bytes to text incrementally
                    buffer += decoder.decode(chunk, final=False)

                    if len(buffer) >= chunk_size:
                        yield self._create_chunk(buffer, str(resolved_path), page_counter)
                        buffer = ""
                        page_counter += 1

        except UnicodeDecodeError as e:
            msg = "File must be strictly UTF-8 encoded"
            raise ProcessingError(msg) from e
        except Exception as e:
            msg = f"Failed to process document: {e}"
            raise ProcessingError(msg) from e

    def _create_chunk(self, text: str, source: str, page: int) -> SemanticChunk:
        return SemanticChunk(
            id=str(uuid.uuid4()),
            text=text,
            metadata=ChunkMetadata(
                source_document=source,
                page_number=page,
                entities_extracted=[],
            )
        )
