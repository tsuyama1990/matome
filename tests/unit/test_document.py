"""Unit tests for domain models."""

import uuid

import pytest
from pydantic import ValidationError

from src.domain_models.document import (
    ChunkMetadata,
    GraphNode,
    SemanticChunk,
    SourceDocument,
)


def test_chunk_metadata_valid() -> None:
    """Test valid ChunkMetadata creation."""
    metadata = ChunkMetadata(
        source_doc_id=uuid.uuid4(),
        start_index=0,
        end_index=10,
        entities=["test"],
    )
    assert metadata.start_index == 0
    assert metadata.end_index == 10


def test_chunk_metadata_invalid_indices() -> None:
    """Test invalid ChunkMetadata indices."""
    with pytest.raises(ValidationError):
        ChunkMetadata(
            source_doc_id=uuid.uuid4(),
            start_index=10,
            end_index=0,
            entities=["test"],
        )


def test_chunk_metadata_extra_forbid() -> None:
    """Test extra fields are forbidden."""
    with pytest.raises(ValidationError):
        ChunkMetadata(
            source_doc_id=uuid.uuid4(),
            start_index=0,
            end_index=10,
            entities=["test"],
            extra_field="test",  # type: ignore[call-arg]
        )


def test_semantic_chunk_valid() -> None:
    """Test valid SemanticChunk creation."""
    metadata = ChunkMetadata(
        source_doc_id=uuid.uuid4(),
        start_index=0,
        end_index=10,
        entities=["test"],
    )
    chunk = SemanticChunk(content="test content", metadata=metadata)
    assert chunk.content == "test content"
    assert chunk.metadata == metadata


def test_graph_node_valid() -> None:
    """Test valid GraphNode creation."""
    node = GraphNode(level=1, summary="test summary")
    assert node.level == 1
    assert node.summary == "test summary"
    assert not node.is_unlocked


def test_source_document_valid() -> None:
    """Test valid SourceDocument creation."""
    doc = SourceDocument(filename="test.txt", file_type="text/plain")
    assert doc.filename == "test.txt"
    assert doc.file_type == "text/plain"


def test_source_document_empty_filename() -> None:
    """Test empty filename fails validation."""
    with pytest.raises(ValidationError):
        SourceDocument(filename="", file_type="text/plain")
