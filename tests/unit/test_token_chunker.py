import pytest

from domain_models.config import ProcessingConfig
from domain_models.manifest import Chunk
from matome.engines.token_chunker import JapaneseTokenChunker


def test_chunker_basic() -> None:
    """Test basic chunking functionality."""
    chunker = JapaneseTokenChunker()
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

    chunker = JapaneseTokenChunker()
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

def test_chunker_invalid_model_fallback(caplog: pytest.LogCaptureFixture) -> None:
    """Test fallback to cl100k_base when invalid model is provided."""
    # This should trigger a warning log and fallback
    chunker = JapaneseTokenChunker(model_name="invalid_model_name_that_does_not_exist")
    assert chunker.tokenizer.name == "cl100k_base"
    assert "Tokenizer loading failed" in caplog.text

def test_chunker_security_long_model_name() -> None:
    """Test that extremely long model names trigger validation error (fallback)."""
    long_name = "a" * 100
    chunker = JapaneseTokenChunker(model_name=long_name)
    assert chunker.tokenizer.name == "cl100k_base"

def test_chunker_empty_input() -> None:
    """Test that empty input returns an empty list."""
    chunker = JapaneseTokenChunker()
    config = ProcessingConfig()
    chunks = chunker.split_text("", config)
    assert chunks == []

    chunks_none = chunker.split_text(None, config) # type: ignore
    assert chunks_none == []

def test_chunker_single_sentence_exceeds_limit() -> None:
    """Test behavior when a single sentence exceeds max_tokens."""
    chunker = JapaneseTokenChunker()
    # Create a sentence longer than limit
    # 'a' is 1 token in cl100k_base.
    long_sentence = "a" * 150 + "。"
    config = ProcessingConfig(max_tokens=100)

    # Current behavior: it appends the sentence even if it exceeds limits (no recursive splitting yet)
    chunks = chunker.split_text(long_sentence, config)

    assert len(chunks) == 1
    assert chunks[0].text == long_sentence
    # Ensure it didn't crash

def test_chunker_unicode() -> None:
    """Test handling of emojis and special unicode characters."""
    chunker = JapaneseTokenChunker()
    text = "Hello 🌍! This is a test 🧪. 日本語もOKですか？はい。"
    config = ProcessingConfig(max_tokens=50)
    chunks = chunker.split_text(text, config)

    assert len(chunks) > 0
    reconstructed = "".join(c.text for c in chunks)
    # normalization might change chars? NFKC preserves emojis usually
    assert "🌍" in reconstructed
    assert "🧪" in reconstructed
    assert "日本語" in reconstructed

def test_chunker_very_long_input() -> None:
    """Test performance/recursion on very long input."""
    # Create a massive string of repeated sentences
    # 10,000 sentences * ~10 chars = 100,000 chars
    text = "これはテストです。" * 10000
    chunker = JapaneseTokenChunker()
    config = ProcessingConfig(max_tokens=1000)

    chunks = chunker.split_text(text, config)
    assert len(chunks) > 0
    # Should be roughly 100k chars / (1000 tokens * ~2 chars/token) = ~50 chunks?
    # Exact number doesn't matter as much as completion without error.
