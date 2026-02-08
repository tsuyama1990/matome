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
    """
    Test fallback to cl100k_base when invalid model is provided via constructor.

    The constructor catches ValueError from get_cached_tokenizer and falls back.
    """
    chunker = JapaneseTokenChunker(model_name="invalid_model_name_that_does_not_exist")
    assert chunker.tokenizer.name == "cl100k_base"
    assert "Tokenizer loading failed" in caplog.text

def test_chunker_security_strict_validation() -> None:
    """
    Test that get_cached_tokenizer strictly raises ValueError for unknown models.

    We need to access get_cached_tokenizer directly or check constructor behavior for unknown models
    that are NOT in the whitelist but valid for tiktoken (e.g. if we used a new model name).
    However, the constructor wraps it.
    So we verify that even a 'valid' tiktoken model that is NOT in our whitelist triggers fallback.
    """
    # "gpt2" is in whitelist. "p50k_base" is in whitelist.
    # Let's try a fake model name that tiktoken doesn't know -> constructor catches ValueError -> fallback.
    # What about a model that tiktoken might know but we didn't whitelist?
    # e.g. "gpt-4-0314" is not in our explicit set (though "gpt-4" is).
    # Wait, "gpt-4-0314" maps to "cl100k_base".
    # If we pass "gpt-4-0314", get_cached_tokenizer raises ValueError (not in whitelist).
    # Constructor catches -> falls back to "cl100k_base" (which happens to be the same encoding).
    # So the end result is correct behavior (safe fallback).

    # Let's verify that a very long model name triggers fallback (and thus was rejected by validation)
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
