from unittest.mock import MagicMock

import pytest

from domain_models.config import ProcessingConfig
from matome.engines.embedder import EmbeddingService
from matome.engines.semantic_chunker import JapaneseSemanticChunker


@pytest.fixture
def mock_embedder() -> MagicMock:
    # Mock embed_strings to return simple vectors
    return MagicMock(spec=EmbeddingService)


def test_semantic_chunker_merging_percentile(mock_embedder: MagicMock) -> None:
    # Setup: 3 sentences.
    # S1-S2: Sim=1.0 (Dist=0.0)
    # S2-S3: Sim=0.0 (Dist=1.0)
    # Distances are [0.0, 1.0]
    text = "文1。文2。文3。"

    # Return vectors: S1=[1,0], S2=[1,0], S3=[0,1]
    mock_embedder.embed_strings.return_value = [[1.0, 0.0], [1.0, 0.0], [0.0, 1.0]]

    chunker = JapaneseSemanticChunker(mock_embedder)

    # Percentile 90: Threshold = 0.9 (approx)
    # 0.0 < 0.9 -> Merge
    # 1.0 > 0.9 -> Split
    config = ProcessingConfig(semantic_chunking_percentile=90, max_tokens=100)

    chunks = list(chunker.split_text(text, config))

    # Expect: Chunk 1 = "文1。文2。", Chunk 2 = "文3。"
    assert len(chunks) == 2
    assert chunks[0].text == "文1。文2。"
    assert chunks[1].text == "文3。"


def test_semantic_chunker_max_tokens(mock_embedder: MagicMock) -> None:
    # Setup: 2 sentences, similar, but max_tokens limits merging.
    text = "長い文1。長い文2。"

    mock_embedder.embed_strings.return_value = [[1.0, 0.0], [1.0, 0.0]]

    chunker = JapaneseSemanticChunker(mock_embedder)
    # len("長い文1。") + len("長い文2。") = 10.
    # Set max_tokens = 8.
    config = ProcessingConfig(semantic_chunking_percentile=90, max_tokens=8)

    chunks = list(chunker.split_text(text, config))

    assert len(chunks) == 2
    assert chunks[0].text == "長い文1。"
    assert chunks[1].text == "長い文2。"


def test_empty_text(mock_embedder: MagicMock) -> None:
    chunker = JapaneseSemanticChunker(mock_embedder)
    config = ProcessingConfig()
    assert list(chunker.split_text("", config)) == []


def test_split_text_edge_cases(mock_embedder: MagicMock) -> None:
    """Test handling of edge cases like empty strings and whitespace."""
    chunker = JapaneseSemanticChunker(mock_embedder)
    config = ProcessingConfig()

    # Whitespace only
    assert list(chunker.split_text("   \n   ", config)) == []

    # Invalid input type
    with pytest.raises(TypeError, match="Input text must be a string"):
        list(chunker.split_text(123, config))  # type: ignore[arg-type]


def test_split_text_special_characters(mock_embedder: MagicMock) -> None:
    """Test handling of special characters and very short sentences."""
    chunker = JapaneseSemanticChunker(mock_embedder)
    config = ProcessingConfig()

    # Special characters
    text = "Test! @#$%^&*()_+ 123.\nAnother line."

    mock_embedder.embed_strings.return_value = [
        [1.0, 0.0],
        [0.0, 1.0],
    ]

    chunks = list(chunker.split_text(text, config))
    assert len(chunks) > 0
    # For 2 sentences (1 gap), threshold == distance, so merge unless > threshold.
    # With 90th percentile of [1.0], threshold is 1.0. 1.0 > 1.0 is False.
    assert "Test!" in chunks[0].text
    assert "Another line." in chunks[0].text
