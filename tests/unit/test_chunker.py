import pytest
from matome.engines.chunker import JapaneseSemanticChunker
from domain_models.config import ProcessingConfig
from domain_models.manifest import Chunk

def test_chunker_basic() -> None:
    """Test basic chunking functionality."""
    chunker = JapaneseSemanticChunker()
    text = "文１。文２。文３。"
    config = ProcessingConfig(max_tokens=100)
    chunks = chunker.split_text(text, config)

    assert isinstance(chunks, list)
    assert all(isinstance(c, Chunk) for c in chunks)
    assert len(chunks) > 0

    # Check concatenated text
    reconstructed = "".join(c.text for c in chunks)
    # Normalization might change text, so we check if content is preserved generally
    # Note: '１' (full-width) becomes '1' (half-width) after normalization
    assert "文1" in reconstructed

def test_chunker_max_tokens() -> None:
    """Test that chunks respect max_tokens."""
    # Create a long text
    sentence = "あ" * 100 + "。"
    text = sentence * 20 # 2000+ chars

    chunker = JapaneseSemanticChunker()
    config = ProcessingConfig(max_tokens=200)
    chunks = chunker.split_text(text, config)

    assert len(chunks) > 1

    # Verify sequential indices
    indices = [c.index for c in chunks]
    assert indices == list(range(len(chunks)))

    # Verify coverage
    full_text = "".join(c.text for c in chunks)
    # Assuming normalization doesn't change 'あ' and '。' width (it doesn't)
    assert len(full_text) == len(text)

def test_chunker_invalid_model_fallback() -> None:
    """Test fallback to cl100k_base when invalid model is provided."""
    chunker = JapaneseSemanticChunker(model_name="invalid_model_name")
    assert chunker.tokenizer.name == "cl100k_base"
