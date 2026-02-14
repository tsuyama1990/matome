import pytest
from pydantic import ValidationError

from domain_models.config import ProcessingConfig
from domain_models.manifest import Chunk, Document, NodeMetadata, SummaryNode
from domain_models.types import DIKWLevel


def test_document_creation() -> None:
    doc = Document(content="Hello world", metadata={"filename": "test.txt"})
    assert doc.content == "Hello world"
    assert doc.metadata["filename"] == "test.txt"


def test_chunk_validation() -> None:
    # Valid chunk
    chunk = Chunk(
        index=0,
        text="Valid text",
        start_char_idx=0,
        end_char_idx=10,
        embedding=[0.1, 0.2]
    )
    assert chunk.text == "Valid text"

    # Invalid indices
    with pytest.raises(ValidationError):
        Chunk(index=0, text="Text", start_char_idx=10, end_char_idx=5)

    # Empty text
    with pytest.raises(ValidationError):
        Chunk(index=0, text="", start_char_idx=0, end_char_idx=0)


def test_summary_node_defaults() -> None:
    node = SummaryNode(
        id="node1",
        text="Summary",
        level=1,
        children_indices=[1, 2],
        metadata=NodeMetadata()
    )
    assert node.metadata.dikw_level == DIKWLevel.DATA
    assert not node.metadata.is_user_edited


def test_config_validation() -> None:
    # Test valid config
    config = ProcessingConfig()
    assert config.max_tokens > 0

    # Test invalid semantic chunking threshold
    with pytest.raises(ValidationError):
        ProcessingConfig(semantic_chunking_mode=True, semantic_chunking_threshold=1.5)

    # Test invalid model name (whitelist)
    with pytest.raises(ValidationError, match="Embedding model .* is not allowed"):
        ProcessingConfig(embedding_model="malicious_model")
