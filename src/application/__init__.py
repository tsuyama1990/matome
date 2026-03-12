"""
Application layer containing orchestration workflows, use cases, and AI services.
"""

import re
import uuid
from pathlib import Path
from typing import Any

from langgraph.graph import StateGraph

from src.domain_models.document import ChunkMetadata, SemanticChunk
from src.domain_models.exceptions import ProcessingError
from src.domain_models.graph_state import GraphState, ProcessingStatus


class BaseTestParsingService:
    """A dummy deterministic parsing service."""

    def parse(self, filepath: str) -> str:
        """Parses a file by simply reading it."""
        try:
            p = Path(filepath)
            with p.open(encoding="utf-8") as f:
                return f.read()
        except FileNotFoundError as e:
            msg = f"File not found: {filepath}"
            raise ProcessingError(msg) from e
        except Exception as e:
            msg = f"Error parsing file: {e}"
            raise ProcessingError(msg) from e


class BaseTestChunkingService:
    """A dummy deterministic chunking service using bounded regex."""

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


def _validate_document_presence(state: GraphState) -> None:
    """Validates that a document is present in the state."""
    if state.current_document is None:
        msg = "Missing document."
        raise ProcessingError(msg)


def parse_file_node(state_dict: dict[str, Any]) -> dict[str, Any]:
    """Node that parses the file into an EnrichedDocument."""
    state = GraphState(**state_dict)
    if state.current_document is None:
        msg = "No document provided in state."
        state.add_error(msg)
        state.transition_status(ProcessingStatus.FAILED)
        return state.model_dump()

    try:
        parser = BaseTestParsingService()
        if state.current_document is not None:
            filepath = state.current_document.original_text
            content = parser.parse(filepath)

            # In this dummy implementation, original_text stored the filepath initially.
            # Now we replace it with the parsed content.
            state.current_document.original_text = content
            state.transition_status(ProcessingStatus.CHUNKING)

    except ProcessingError as e:
        state.add_error(str(e))
        state.transition_status(ProcessingStatus.FAILED)

    return state.model_dump()


def chunk_text_node(state_dict: dict[str, Any]) -> dict[str, Any]:
    """Node that chunks the parsed text."""
    state = GraphState(**state_dict)

    if state.processing_status != ProcessingStatus.CHUNKING:
        return state.model_dump()

    try:
        _validate_document_presence(state)

        chunker = BaseTestChunkingService()
        if state.current_document is not None:
            text = state.current_document.original_text
            source_file = str(state.current_document.document_id)

            chunks = chunker.chunk_text(text, source_file)
            state.current_document.chunks = chunks
            state.transition_status(ProcessingStatus.EMBEDDING)

    except ProcessingError as e:
        state.add_error(str(e))
        state.transition_status(ProcessingStatus.FAILED)

    return state.model_dump()


def build_ingestion_graph() -> Any:
    """Builds and compiles the ingestion workflow graph."""
    # We use dict as the state type for LangGraph to avoid Pydantic strict typing issues
    # with LangGraph's internal Pregel overloads.
    workflow = StateGraph(dict)  # type: ignore[type-var]

    workflow.add_node("parse", parse_file_node)  # type: ignore[call-overload]
    workflow.add_node("chunk", chunk_text_node)  # type: ignore[call-overload]

    workflow.set_entry_point("parse")
    workflow.add_edge("parse", "chunk")
    workflow.set_finish_point("chunk")

    return workflow.compile()
