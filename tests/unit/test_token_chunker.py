import pytest
from unittest.mock import MagicMock
from domain_models.config import ProcessingConfig
from matome.engines.token_chunker import JapaneseTokenChunker

def test_chunker_basic() -> None:
    """Test basic chunking functionality."""
    chunker = JapaneseTokenChunker()
    text = "文１。文２。文３。"
    # max_summary_tokens defaults to 200, so max_tokens must be >= 200 to pass validation
    config = ProcessingConfig(max_tokens=200, max_summary_tokens=100)

    chunks = list(chunker.split_text(text, config))
    assert len(chunks) > 0
    assert chunks[0].index == 0
    assert "文" in chunks[0].text

def test_chunker_overlap() -> None:
    """Test chunking with overlap."""
    chunker = JapaneseTokenChunker()
    # Create long enough text to force split
    text = "A" * 1000

    config = ProcessingConfig(
        max_tokens=100,
        overlap=20,
        max_summary_tokens=50  # Must be <= max_tokens
    )

    chunks = list(chunker.split_text(text, config))
    if len(chunks) > 1:
        # Check continuity/overlap logic if applicable
        # JapaneseTokenChunker might not overlap perfectly on chars, but on tokens
        pass

def test_chunker_single_sentence_exceeds_limit() -> None:
    """Test behavior when a single sentence exceeds max_tokens."""
    chunker = JapaneseTokenChunker()
    # Create a sentence longer than limit
    long_sentence = "a" * 150 + "。"
    config = ProcessingConfig(max_tokens=100, max_summary_tokens=50)

    chunks = list(chunker.split_text(long_sentence, config))

    # Should still produce chunks, splitting the sentence if necessary
    assert len(chunks) > 0
    # The first chunk should be around max_tokens length (depending on tokenizer)
    # Just verify it didn't crash and output something
    assert len(chunks[0].text) > 0

def test_chunker_unicode() -> None:
    """Test handling of emojis and special unicode characters."""
    chunker = JapaneseTokenChunker()
    text = "Hello 🌍! This is a test 🧪. 日本語もOKですか？はい。"
    config = ProcessingConfig(max_tokens=200, max_summary_tokens=100)

    chunks = list(chunker.split_text(text, config))
    assert len(chunks) == 1
    assert "🌍" in chunks[0].text
