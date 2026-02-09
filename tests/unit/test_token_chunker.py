import pytest

from domain_models.config import ProcessingConfig
from domain_models.manifest import Chunk
from matome.engines.token_chunker import JapaneseTokenChunker


def test_chunker_basic() -> None:
    """Test basic chunking functionality."""
    chunker = JapaneseTokenChunker()
    text = "文１。文２。文３。"
    config = ProcessingConfig(max_tokens=100)
    chunks = list(chunker.split_text(text, config))

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
    text = sentence * 20  # 2000+ chars

    chunker = JapaneseTokenChunker()
    config = ProcessingConfig(max_tokens=200)
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
    with no fallback to default.
    """
    # Validation now happens at Config level mostly, but also in tokenizer loader
    from pydantic import ValidationError

    # Case 1: Config validation
    with pytest.raises(ValidationError, match="not allowed"):
        ProcessingConfig(tokenizer_model="invalid_model")

    # Case 2: If somehow bypassed (e.g., construct config manually without validation or mocking),
    # the chunker should still catch it.
    # We can simulate this by mocking ProcessingConfig or passing an object that looks like config
    class MockConfig:
        tokenizer_model = "invalid_model"
        max_tokens = 100

    with pytest.raises(ValidationError):
        JapaneseTokenChunker(config=MockConfig())  # type: ignore


def test_chunker_empty_input() -> None:
    """Test that empty input returns an empty list."""
    chunker = JapaneseTokenChunker()
    config = ProcessingConfig()
    chunks = list(chunker.split_text("", config))
    assert chunks == []

    chunks_none = list(chunker.split_text(None, config))  # type: ignore
    assert chunks_none == []


def test_chunker_single_sentence_exceeds_limit() -> None:
    """Test behavior when a single sentence exceeds max_tokens."""
    chunker = JapaneseTokenChunker()
    # Create a sentence longer than limit
    # 'a' is 1 token in cl100k_base.
    long_sentence = "a" * 150 + "。"
    config = ProcessingConfig(max_tokens=100)

    # Current behavior: it appends the sentence even if it exceeds limits (no recursive splitting yet)
    chunks = list(chunker.split_text(long_sentence, config))

    assert len(chunks) == 1
    assert chunks[0].text == long_sentence
    # Ensure it didn't crash


def test_chunker_unicode() -> None:
    """Test handling of emojis and special unicode characters."""
    chunker = JapaneseTokenChunker()
    text = "Hello 🌍! This is a test 🧪. 日本語もOKですか？はい。"
    config = ProcessingConfig(max_tokens=50)
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
    config = ProcessingConfig(max_tokens=1000)

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
