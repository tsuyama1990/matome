from unittest.mock import MagicMock

import pytest

from domain_models.config import ProcessingConfig
from matome.engines.embedder import EmbeddingService
from matome.engines.semantic_chunker import JapaneseSemanticChunker


@pytest.fixture
def mock_embedder() -> MagicMock:
    # Mock embed_strings to return simple vectors
    # We will control the output in tests
    return MagicMock(spec=EmbeddingService)


def test_semantic_chunker_merging(mock_embedder: MagicMock) -> None:
    # Setup: 3 sentences.
    # S1 and S2 are similar (sim=1.0). S3 is different (sim=0.0).
    text = "文1。文2。文3。"

    # embed_strings will be called with ["文1。", "文2。", "文3。"]
    # Return vectors: S1=[1,0], S2=[1,0], S3=[0,1]
    mock_embedder.embed_strings.return_value = iter([[1.0, 0.0], [1.0, 0.0], [0.0, 1.0]])

    chunker = JapaneseSemanticChunker(mock_embedder)
    config = ProcessingConfig(semantic_chunking_threshold=0.9, max_tokens=100)

    chunks = chunker.split_text(text, config)

    # Expect: Chunk 1 = "文1。文2。", Chunk 2 = "文3。"
    assert len(chunks) == 2
    assert chunks[0].text == "文1。文2。"
    assert chunks[1].text == "文3。"


def test_semantic_chunker_max_tokens(mock_embedder: MagicMock) -> None:
    # Setup: 2 sentences, similar, but max_tokens limits merging.
    text = "長い文1。長い文2。"

    mock_embedder.embed_strings.return_value = iter([[1.0, 0.0], [1.0, 0.0]])

    chunker = JapaneseSemanticChunker(mock_embedder)
    # Set max_tokens very low to force split even if similar
    # Length of "長い文1。" is 5 chars. Assume check is generous but strict enough.
    # In implementation we used strict len() check against max_tokens.
    # len("長い文1。") + len("長い文2。") = 10.
    # Set max_tokens = 8.
    config = ProcessingConfig(semantic_chunking_threshold=0.5, max_tokens=8)

    chunks = chunker.split_text(text, config)

    assert len(chunks) == 2
    assert chunks[0].text == "長い文1。"
    assert chunks[1].text == "長い文2。"


def test_empty_text(mock_embedder: MagicMock) -> None:
    chunker = JapaneseSemanticChunker(mock_embedder)
    config = ProcessingConfig()
    assert chunker.split_text("", config) == []


def test_split_text_edge_cases(mock_embedder: MagicMock) -> None:
    """Test handling of edge cases like empty strings and whitespace."""
    chunker = JapaneseSemanticChunker(mock_embedder)
    config = ProcessingConfig()

    # Whitespace only
    assert chunker.split_text("   \n   ", config) == []

    # Invalid input type
    with pytest.raises(TypeError, match="Input text must be a string"):
        chunker.split_text(123, config)  # type: ignore[arg-type]


def test_split_text_special_characters(mock_embedder: MagicMock) -> None:
    """Test handling of special characters and very short sentences."""
    chunker = JapaneseSemanticChunker(mock_embedder)
    config = ProcessingConfig()

    # Special characters that might confuse regex or normalization
    text = "Test! @#$%^&*()_+ 123.\nAnother line."

    mock_embedder.embed_strings.return_value = iter(
        [
            [1.0, 0.0],  # Test! ...
            [0.0, 1.0],  # Another line.
        ]
    )

    chunks = chunker.split_text(text, config)
    assert len(chunks) > 0
    assert "Test!" in chunks[0].text

    # Very short sentence
    text_short = "A. B."
    mock_embedder.embed_strings.return_value = iter([[1.0], [1.0]])
    chunks_short = chunker.split_text(text_short, config)
    assert len(chunks_short) > 0
    assert "A." in chunks_short[0].text
