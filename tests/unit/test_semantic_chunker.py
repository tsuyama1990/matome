from unittest.mock import MagicMock

import pytest
import numpy as np

from domain_models.config import ProcessingConfig
from matome.engines.embedder import EmbeddingService
from matome.engines.semantic_chunker import JapaneseSemanticChunker


@pytest.fixture
def mock_embedder() -> MagicMock:
    return MagicMock(spec=EmbeddingService)


def test_semantic_chunker_percentile_split(mock_embedder: MagicMock) -> None:
    # Setup: 4 sentences.
    # S1-S2: Similar (dist low)
    # S2-S3: Different (dist high) -> Should split here
    # S3-S4: Similar (dist low)
    text = "S1。S2。S3。S4。"

    # Embeddings:
    # S1 = [1, 0]
    # S2 = [1, 0] (Sim=1.0, Dist=0.0)
    # S3 = [0, 1] (Sim=0.0, Dist=1.0)
    # S4 = [0, 1] (Sim=1.0, Dist=0.0)

    # Distances will be: [0.0, 1.0, 0.0]
    # Percentile 90 of [0, 0, 1] is ~0.8.
    # Threshold = 0.8.
    # D1(0) > 0.8? No.
    # D2(1) > 0.8? Yes -> Split after S2.
    # D3(0) > 0.8? No.

    # Expected Chunks: [S1+S2], [S3+S4]

    mock_embedder.embed_strings.return_value = iter([
        [1.0, 0.0],
        [1.0, 0.0],
        [0.0, 1.0],
        [0.0, 1.0]
    ])

    chunker = JapaneseSemanticChunker(mock_embedder)
    config = ProcessingConfig(semantic_chunking_percentile=90, max_tokens=100)

    chunks = list(chunker.split_text(text, config))

    assert len(chunks) == 2
    assert chunks[0].text == "S1。S2。"
    assert chunks[1].text == "S3。S4。"


def test_semantic_chunker_max_tokens_force_split(mock_embedder: MagicMock) -> None:
    # Setup: 2 sentences, identical embeddings.
    # Should merge by semantics, but max_tokens forces split.
    text = "A。B。"

    # Dist = 0.0. Threshold will be 0.0.
    # 0 > 0 is False.
    # But max_tokens is tiny.

    mock_embedder.embed_strings.return_value = iter([
        [1.0, 0.0],
        [1.0, 0.0]
    ])

    chunker = JapaneseSemanticChunker(mock_embedder)
    # "A。" len=2. Total 4. Max=3 -> Must split.
    config = ProcessingConfig(semantic_chunking_percentile=90, max_tokens=3)

    chunks = list(chunker.split_text(text, config))

    assert len(chunks) == 2
    assert chunks[0].text == "A。"
    assert chunks[1].text == "B。"


def test_empty_text(mock_embedder: MagicMock) -> None:
    chunker = JapaneseSemanticChunker(mock_embedder)
    config = ProcessingConfig()
    assert list(chunker.split_text("", config)) == []


def test_single_sentence(mock_embedder: MagicMock) -> None:
    chunker = JapaneseSemanticChunker(mock_embedder)
    config = ProcessingConfig()
    text = "Only one."

    # Should yield 1 chunk without calling embedder?
    # Logic: iter_sentences -> 1 item.
    # n_sentences == 1 -> yield immediately.

    chunks = list(chunker.split_text(text, config))
    assert len(chunks) == 1
    assert chunks[0].text == "Only one."

    # Verify embedder was NOT called (optimization)
    mock_embedder.embed_strings.assert_not_called()


def test_split_text_edge_cases(mock_embedder: MagicMock) -> None:
    """Test handling of edge cases like empty strings and whitespace."""
    chunker = JapaneseSemanticChunker(mock_embedder)
    config = ProcessingConfig()

    # Whitespace only
    assert list(chunker.split_text("   \n   ", config)) == []

    # Invalid input type
    with pytest.raises(TypeError, match="Input text must be a string"):
        list(chunker.split_text(123, config))  # type: ignore[arg-type]
