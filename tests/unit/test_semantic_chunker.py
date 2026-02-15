from unittest.mock import MagicMock

import pytest

from domain_models.config import ProcessingConfig
from matome.engines.semantic_chunker import JapaneseSemanticChunker


@pytest.fixture
def mock_embedder() -> MagicMock:
    return MagicMock()

def test_semantic_chunker_basic(mock_embedder: MagicMock) -> None:
    text = "文1。文2。文3。"
    # S1, S2 similar. S3 different.
    # Sim(S1, S2) = 1.0 (merged)
    # Sim(S2, S3) = 0.0 (split)

    # embed_strings is called for each sentence
    mock_embedder.embed_strings.return_value = [[1.0, 0.0], [1.0, 0.0], [0.0, 1.0]]

    chunker = JapaneseSemanticChunker(mock_embedder)

    # Config: Threshold 0.9.
    # 1.0 >= 0.9 -> Merge
    # 0.0 < 0.9 -> Split
    config = ProcessingConfig(
        semantic_chunking_mode=True,
        semantic_chunking_threshold=0.9,
        max_tokens=200,
        max_summary_tokens=100
    )

    chunks = list(chunker.split_text(text, config))

    assert len(chunks) == 2
    assert "文1。文2。" in chunks[0].text
    assert "文3。" in chunks[1].text

def test_semantic_chunker_merging_percentile(mock_embedder: MagicMock) -> None:
    text = "文1。文2。文3。"

    # Return vectors: S1=[1,0], S2=[1,0], S3=[0,1]
    mock_embedder.embed_strings.return_value = [[1.0, 0.0], [1.0, 0.0], [0.0, 1.0]]

    chunker = JapaneseSemanticChunker(mock_embedder)

    # Percentile 90: Threshold = 0.9 (approx)
    # 0.0 < 0.9 -> Merge
    # 1.0 > 0.9 -> Split
    # Actually percentile logic calculates threshold dynamically from distances.
    # Distances: d(S1,S2)=0, d(S2,S3)=1.414
    # 90th percentile of [0, 1.414] is approx 1.2
    # Break if dist > threshold.
    # 0 < 1.2 -> Merge
    # 1.414 > 1.2 -> Split

    config = ProcessingConfig(
        semantic_chunking_percentile=90,
        max_tokens=200,
        max_summary_tokens=100
    )

    chunks = list(chunker.split_text(text, config))
    # Expect split after S2
    assert len(chunks) == 2

def test_semantic_chunker_max_tokens(mock_embedder: MagicMock) -> None:
    # Setup: 2 sentences, similar, but max_tokens limits merging.
    text = "長い文1。長い文2。"

    mock_embedder.embed_strings.return_value = [[1.0, 0.0], [1.0, 0.0]]

    chunker = JapaneseSemanticChunker(mock_embedder)
    # len("長い文1。") + len("長い文2。") = 10.
    # Set max_tokens = 8.
    config = ProcessingConfig(
        semantic_chunking_percentile=90,
        max_tokens=8,
        max_summary_tokens=4 # Consistent
    )

    chunks = list(chunker.split_text(text, config))

    # Should not merge because total length > max_tokens
    assert len(chunks) == 2
    assert chunks[0].text == "長い文1。"
    assert chunks[1].text == "長い文2。"
