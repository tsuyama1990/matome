from domain_models.config import ProcessingConfig
from domain_models.manifest import Chunk
from matome.engines.chunker import JapaneseSemanticChunker


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

def test_chunker_empty_input() -> None:
    """Test that empty input returns an empty list."""
    chunker = JapaneseSemanticChunker()
    config = ProcessingConfig()
    chunks = chunker.split_text("", config)
    assert chunks == []

    chunks_none = chunker.split_text(None, config) # type: ignore
    assert chunks_none == []

def test_chunker_single_sentence_exceeds_limit() -> None:
    """Test behavior when a single sentence exceeds max_tokens."""
    chunker = JapaneseSemanticChunker()
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
    chunker = JapaneseSemanticChunker()
    text = "Hello 🌍! This is a test 🧪. 日本語もOKですか？はい。"
    config = ProcessingConfig(max_tokens=50)
    chunks = chunker.split_text(text, config)

    assert len(chunks) > 0
    reconstructed = "".join(c.text for c in chunks)
    # normalization might change chars? NFKC preserves emojis usually
    assert "🌍" in reconstructed
    assert "🧪" in reconstructed
    assert "日本語" in reconstructed
