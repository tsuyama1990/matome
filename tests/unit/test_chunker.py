from collections.abc import Iterator

import pytest

from domain_models.config import ChunkingConfig, ProcessingConfig
from domain_models.manifest import Chunk
from matome.engines.chunker import JapaneseTokenChunker


def test_chunker_basic() -> None:
    """Test basic chunking functionality."""
    chunker = JapaneseTokenChunker()
    text = "文１。文２。文３。"
    config = ProcessingConfig(chunking=ChunkingConfig(max_tokens=100))
    # consume iterator
    chunks = list(chunker.split_text(text, config))

    assert isinstance(chunks, list)
    assert all(isinstance(c, Chunk) for c in chunks)
    assert len(chunks) > 0

    # Check concatenated text
    reconstructed = "".join(c.text for c in chunks)
    # Normalization might change text, so we check if content is preserved generally
    # Note: '１' (full-width) becomes '1' (half-width) after normalization
    assert "文1" in reconstructed

def test_chunker_streaming() -> None:
    """Test chunking with an iterable stream."""
    chunker = JapaneseTokenChunker()

    def text_stream() -> Iterator[str]:
        yield "これは"
        yield "テストです。"
        yield "次の文。"

    config = ProcessingConfig(chunking=ChunkingConfig(max_tokens=100))
    chunks = list(chunker.split_text(text_stream(), config))

    assert len(chunks) > 0
    full_text = "".join(c.text for c in chunks)
    assert "これはテストです。" in full_text
    assert "次の文。" in full_text

def test_chunker_max_tokens() -> None:
    """Test that chunks respect max_tokens."""
    # Create a long text
    sentence = "あ" * 100 + "。"
    text = sentence * 20 # 2000+ chars

    chunker = JapaneseTokenChunker()
    config = ProcessingConfig(chunking=ChunkingConfig(max_tokens=200))
    chunks = list(chunker.split_text(text, config))

    assert len(chunks) > 1

    # Verify sequential indices
    indices = [c.index for c in chunks]
    assert indices == list(range(len(chunks)))

    # Verify coverage
    full_text = "".join(c.text for c in chunks)
    # Assuming normalization doesn't change 'あ' and '。' width (it doesn't)
    assert len(full_text) == len(text)

def test_chunker_invalid_model_security() -> None:
    """
    Test that invalid model names (not in whitelist) raise ValueError immediately,
    and verify the error message content.
    """
    # Test initialization (if provided)
    with pytest.raises(ValueError, match="not in the allowed list"):
        JapaneseTokenChunker(model_name="gpt-4-turbo-malicious")

    # Test count_tokens
    chunker = JapaneseTokenChunker()
    with pytest.raises(ValueError, match="not in the allowed list"):
        chunker.count_tokens("test", model_name="malicious_model")

def test_chunker_empty_input() -> None:
    """Test that empty input returns an empty list."""
    chunker = JapaneseTokenChunker()
    config = ProcessingConfig()
    chunks = list(chunker.split_text("", config))
    assert chunks == []

    chunks_none = list(chunker.split_text(None, config)) # type: ignore
    assert chunks_none == []

def test_chunker_single_sentence_exceeds_limit() -> None:
    """Test behavior when a single sentence exceeds max_tokens."""
    chunker = JapaneseTokenChunker()
    # Create a sentence longer than limit
    # 'cl100k_base' encodes 'a' as 1 token.
    long_sentence = "a" * 150 + "。"
    config = ProcessingConfig(chunking=ChunkingConfig(max_tokens=100))

    # Current behavior: it appends the sentence even if it exceeds limits (no recursive splitting yet)
    chunks = list(chunker.split_text(long_sentence, config))

    assert len(chunks) == 1
    assert chunks[0].text == long_sentence

    # Verification of token count using words to ensure count > 100
    word_sentence = "word " * 150
    chunks_words = list(chunker.split_text(word_sentence, config))
    token_count_words = chunker.count_tokens(chunks_words[0].text)
    assert token_count_words > 100

def test_chunker_unicode() -> None:
    """Test handling of emojis and special unicode characters."""
    chunker = JapaneseTokenChunker()
    text = "Hello 🌍! This is a test 🧪. 日本語もOKですか？はい。"
    config = ProcessingConfig(chunking=ChunkingConfig(max_tokens=50))
    chunks = list(chunker.split_text(text, config))

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
    config = ProcessingConfig(chunking=ChunkingConfig(max_tokens=1000))

    # Just consume
    chunks = list(chunker.split_text(text, config))
    assert len(chunks) > 0

def test_chunker_count_tokens() -> None:
    """Test the count_tokens method."""
    chunker = JapaneseTokenChunker()

    # Normal case
    text = "hello world"
    count = chunker.count_tokens(text)
    assert count > 0
    assert count == 2

    # Empty case
    assert chunker.count_tokens("") == 0

    # Very long string case
    long_text = "word " * 1000
    assert chunker.count_tokens(long_text) > 0
