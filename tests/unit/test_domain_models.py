import uuid

import pytest
from pydantic import ValidationError

from src.domain_models import ChunkMetadata, EnrichedDocument, GraphState, RaptorNode, SemanticChunk


def test_chunk_metadata_forbids_extra_fields() -> None:
    """Test that ChunkMetadata strictly forbids extra fields."""
    valid_data = {
        "source_file": "test.txt",
        "page_number": 1,
        "extracted_entities": ["Entity1"],
        "time_axis": "Past",
        "actor_axis": "User",
    }
    metadata = ChunkMetadata(**valid_data)  # type: ignore[arg-type]
    assert metadata.source_file == "test.txt"

    invalid_data = valid_data.copy()
    invalid_data["malicious_field"] = "injection_attempt"

    with pytest.raises(ValidationError) as excinfo:
        ChunkMetadata(**invalid_data)  # type: ignore[arg-type]

    assert "Extra inputs are not permitted" in str(excinfo.value)


def test_semantic_chunk_instantiation() -> None:
    """Test standard SemanticChunk instantiation."""
    metadata = ChunkMetadata(source_file="test.txt")
    chunk_id = uuid.uuid4()
    chunk = SemanticChunk(
        id=chunk_id,
        content="This is a test chunk.",
        embedding=[0.1, 0.2, 0.3],
        metadata=metadata,
    )

    assert chunk.id == chunk_id
    assert chunk.content == "This is a test chunk."
    assert chunk.embedding == [0.1, 0.2, 0.3]
    assert chunk.metadata.source_file == "test.txt"


def test_raptor_node_defaults() -> None:
    """Test RaptorNode provides the correct defaults."""
    node = RaptorNode(
        node_id="node-1",
        level=0,
        summarized_content="Root summary",
    )
    assert node.children_ids == []
    assert node.is_unlocked is False


def test_enriched_document_instantiation() -> None:
    """Test EnrichedDocument correctly holds chunks and raptor nodes."""
    doc = EnrichedDocument(
        document_id="doc-1",
        original_text="Full text",
    )
    assert doc.chunks == []
    assert doc.raptor_nodes == []


def test_graph_state_serialization() -> None:
    """Test GraphState serializes and deserializes cleanly without losing data."""
    metadata = ChunkMetadata(source_file="test.txt")
    chunk = SemanticChunk(
        id=uuid.uuid4(),
        content="Test content",
        metadata=metadata,
    )

    doc = EnrichedDocument(
        document_id="doc-1",
        original_text="Full text",
        chunks=[chunk],
    )

    state = GraphState(
        current_document=doc,
        processing_status="processing",
        error_log=["error 1"],
    )

    # Serialize to dict
    state_dict = state.model_dump()

    # Deserialize back to object
    reconstructed_state = GraphState(**state_dict)

    # Compare
    assert reconstructed_state.processing_status == "processing"
    assert reconstructed_state.error_log == ["error 1"]
    assert reconstructed_state.current_document is not None
    assert reconstructed_state.current_document.document_id == "doc-1"
    assert len(reconstructed_state.current_document.chunks) == 1
    assert reconstructed_state.current_document.chunks[0].content == "Test content"
