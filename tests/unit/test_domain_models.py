import uuid
from datetime import UTC

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

    # Needs to be exactly 768 or 1536 float elements long, or empty
    valid_embedding = [0.1] * 768

    chunk = SemanticChunk(
        id=chunk_id,
        content="This is a test chunk.",
        embedding=valid_embedding,
        metadata=metadata,
    )

    assert chunk.id == chunk_id
    assert chunk.content == "This is a test chunk."
    assert chunk.embedding == valid_embedding
    assert chunk.metadata.source_file == "test.txt"


def test_semantic_chunk_embedding_validation_failure() -> None:
    """Test SemanticChunk raises an error if an embedding has the wrong dimensions."""
    metadata = ChunkMetadata(source_file="test.txt")
    chunk_id = uuid.uuid4()

    # Provide incorrect dimensions (3 elements instead of common dimensions)
    invalid_embedding = [0.1, 0.2, 0.3]

    with pytest.raises(ValidationError) as excinfo:
        SemanticChunk(
            id=chunk_id,
            content="This is a test chunk.",
            embedding=invalid_embedding,
            metadata=metadata,
        )

    assert "Embedding length 3 is invalid" in str(excinfo.value)


def test_semantic_chunk_embedding_validation_empty() -> None:
    """Test SemanticChunk raises an error if an embedding is empty."""
    metadata = ChunkMetadata(source_file="test.txt")
    chunk_id = uuid.uuid4()

    with pytest.raises(ValidationError) as excinfo:
        SemanticChunk(
            id=chunk_id,
            content="This is a test chunk.",
            embedding=[],
            metadata=metadata,
        )

    assert "Embedding cannot be empty" in str(excinfo.value)


def test_enriched_document_embedding_consistency() -> None:
    """Test EnrichedDocument validates consistent embedding lengths across all chunks."""
    metadata = ChunkMetadata(source_file="test.txt")

    # Chunk 1: valid 256 embedding
    chunk1 = SemanticChunk(
        id=uuid.uuid4(),
        content="Chunk 1",
        embedding=[0.1] * 256,
        metadata=metadata,
    )

    # Chunk 2: valid 384 embedding (mismatch with chunk 1)
    chunk2 = SemanticChunk(
        id=uuid.uuid4(),
        content="Chunk 2",
        embedding=[0.2] * 384,
        metadata=metadata,
    )

    from src.domain_models.document import DocumentFactory

    with pytest.raises(ValueError, match="Inconsistent embedding dimensions detected"):
        DocumentFactory.create(
            document_id=uuid.uuid4(), original_text="Test", chunks=[chunk1, chunk2], raptor_nodes=[]
        )


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
    doc_id = uuid.uuid4()
    doc = EnrichedDocument(
        document_id=doc_id,
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
        embedding=[0.0] * 768,
        metadata=metadata,
    )

    doc_id = uuid.uuid4()
    doc = EnrichedDocument(
        document_id=doc_id,
        original_text="Full text",
        chunks=[chunk],
    )

    from src.domain_models.graph_state import ProcessingStatus

    state = GraphState(
        current_document=doc,
        processing_status=ProcessingStatus.CHUNKING,
        error_log=["error 1"],
    )

    # Serialize to dict
    state_dict = state.model_dump()

    # Deserialize back to object
    reconstructed_state = GraphState(**state_dict)

    # Compare
    assert reconstructed_state.processing_status == ProcessingStatus.CHUNKING
    assert reconstructed_state.error_log == ["error 1"]
    assert reconstructed_state.clustering_metadata == {}
    assert reconstructed_state.current_document is not None
    assert reconstructed_state.current_document.document_id == doc_id
    assert len(reconstructed_state.current_document.chunks) == 1
    assert reconstructed_state.current_document.chunks[0].content == "Test content"


def test_graph_state_clustering_metadata() -> None:
    """Test GraphState clustering metadata fields are initialized and updatable."""
    state = GraphState()
    assert state.clustering_metadata == {}

    state.clustering_metadata["test_key"] = "test_val"
    assert state.clustering_metadata["test_key"] == "test_val"


def test_graph_state_methods() -> None:
    """Test the GraphState orchestration methods for state transitions."""
    from src.domain_models.graph_state import ProcessingStatus

    state = GraphState()
    assert state.processing_status == ProcessingStatus.INITIAL

    # Override initially to allow typing to check dynamic changes appropriately
    state.processing_status = ProcessingStatus.CHUNKING
    state.transition_status(ProcessingStatus.EMBEDDING)

    # Check string representation to avoid strict literal overlaps in tests
    assert str(state.processing_status) == "EMBEDDING"

    state.transition_status(ProcessingStatus.CLUSTERING)
    assert str(state.processing_status) == "CLUSTERING"

    state.add_error("Network timeout.")
    assert len(state.error_log) == 1
    assert state.error_log[0] == "Network timeout."

    doc_id = uuid.uuid4()
    doc = EnrichedDocument(document_id=doc_id, original_text="Hi")
    state.set_document(doc)
    assert state.current_document is not None
    assert state.current_document.document_id == doc_id


def test_graph_state_invalid_transition() -> None:
    """Test that GraphState raises an error on invalid transitions."""
    from src.domain_models.graph_state import ProcessingStatus

    state = GraphState()
    assert state.processing_status == ProcessingStatus.INITIAL

    with pytest.raises(ValueError, match="Invalid transition from INITIAL to COMPLETE"):
        state.transition_status(ProcessingStatus.COMPLETE)


def test_semantic_chunk_embedding_validation_nan() -> None:
    """Test validation fails if embedding contains NaN or out of bounds."""
    metadata = ChunkMetadata(source_file="test.txt")
    chunk_id = uuid.uuid4()

    invalid_embedding = [0.1] * 767 + [float("nan")]
    with pytest.raises(ValidationError) as excinfo:
        SemanticChunk(
            id=chunk_id,
            content="This is a test chunk.",
            embedding=invalid_embedding,
            metadata=metadata,
        )
    assert "Embedding elements cannot be NaN or Inf" in str(excinfo.value)

    invalid_embedding_inf = [0.1] * 767 + [float("inf")]
    with pytest.raises(ValidationError) as excinfo:
        SemanticChunk(
            id=chunk_id,
            content="This is a test chunk.",
            embedding=invalid_embedding_inf,
            metadata=metadata,
        )
    assert "Embedding elements cannot be NaN or Inf" in str(excinfo.value)

    valid_embedding_bounds = [0.1] * 767 + [1.5]
    chunk = SemanticChunk(
        id=chunk_id,
        content="This is a test chunk.",
        embedding=valid_embedding_bounds,
        metadata=metadata,
    )
    assert chunk.embedding[-1] == 1.5


def test_semantic_chunk_embedding_validation_overflow() -> None:
    """Test validation fails if embedding floats exceed safe overflow ranges."""
    metadata = ChunkMetadata(source_file="test.txt")
    chunk_id = uuid.uuid4()

    invalid_embedding_large = [0.1] * 767 + [1e11]
    with pytest.raises(ValidationError) as excinfo:
        SemanticChunk(
            id=chunk_id,
            content="This is a test chunk.",
            embedding=invalid_embedding_large,
            metadata=metadata,
        )
    assert "Embedding values out of reasonable range." in str(excinfo.value)


def test_unlock_attempt_forbids_extra_fields() -> None:
    from datetime import datetime

    from src.domain_models import UnlockAttempt

    valid_data = {
        "node_id": "test_node_1",
        "user_answer": "This is an answer.",
        "is_correct": True,
        "timestamp": datetime.now(UTC),
    }
    attempt = UnlockAttempt(**valid_data)  # type: ignore[arg-type]
    assert attempt.node_id == "test_node_1"

    invalid_data = valid_data.copy()
    invalid_data["extra_field"] = "not allowed"
    with pytest.raises(ValidationError) as excinfo:
        UnlockAttempt(**invalid_data)  # type: ignore[arg-type]

    assert "Extra inputs are not permitted" in str(excinfo.value)


def test_learning_progress_forbids_extra_fields() -> None:
    from src.domain_models import LearningProgress

    valid_data = {"document_id": uuid.uuid4()}
    progress = LearningProgress(**valid_data)  # type: ignore[arg-type]
    assert progress.unlocked_node_ids == set()
    assert progress.history == []

    invalid_data = valid_data.copy()
    invalid_data["score"] = 100  # type: ignore[assignment]
    with pytest.raises(ValidationError) as excinfo:
        LearningProgress(**invalid_data)  # type: ignore[arg-type]

    assert "Extra inputs are not permitted" in str(excinfo.value)
