import pytest
from pydantic import ValidationError

from domain_models.config import ProcessingConfig
from domain_models.manifest import Chunk, Document


def test_document_validation() -> None:
    """Test valid and invalid Document creation."""
    # Valid
    doc = Document(content="hello", metadata={"source": "test"})
    assert doc.content == "hello"
    assert doc.metadata == {"source": "test"}

    # Invalid: missing content
    with pytest.raises(ValidationError):
        Document(metadata={})  # type: ignore

def test_chunk_validation() -> None:
    """Test valid and invalid Chunk creation."""
    # Valid
    chunk = Chunk(
        index=0,
        text="chunk text",
        start_char_idx=0,
        end_char_idx=10,
        metadata={}
    )
    assert chunk.index == 0
    assert chunk.text == "chunk text"

    # Invalid: negative index
    with pytest.raises(ValidationError):
        Chunk(index=-1, text="text", start_char_idx=0, end_char_idx=10)

def test_config_validation() -> None:
    """Test ProcessingConfig validation."""
    # Valid
    config = ProcessingConfig(max_tokens=100, overlap=10)
    assert config.max_tokens == 100

    # Invalid: zero max_tokens (ge=1)
    with pytest.raises(ValidationError):
        ProcessingConfig(max_tokens=0)
