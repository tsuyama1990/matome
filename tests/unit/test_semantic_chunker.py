from unittest.mock import MagicMock

from domain_models.config import ChunkingConfig, ProcessingConfig
from matome.engines.chunker import JapaneseSemanticChunker


def test_semantic_chunker_basic() -> None:
    """Test basic merging logic with fixed threshold."""
    # Setup
    # 3 sentences: "文1。", "文2。", "文3。"
    # Embeddings: 1 and 2 are similar, 3 is different
    # Sim(1,2) high -> merge
    # Sim(2,3) low -> split

    # Vectors (normalized for simplicity)
    v1 = [1.0, 0.0, 0.0]
    v2 = [0.9, 0.1, 0.0] # High sim with v1
    v3 = [0.0, 0.0, 1.0] # Low sim with v2

    mock_embedder = MagicMock()
    mock_embedder.embed_strings.return_value = [v1, v2, v3]

    chunker = JapaneseSemanticChunker(embedder=mock_embedder)

    # Config: fixed threshold 0.8 (similarity)
    # Distance threshold = 0.2
    # Dist(1,2) ~ small < 0.2 -> merge
    # Dist(2,3) ~ large > 0.2 -> split
    config = ProcessingConfig(
        chunking=ChunkingConfig(
            semantic_chunking_mode="fixed",
            semantic_chunking_threshold=0.8
        )
    )

    text = "文1。文2。文3。"

    # Run
    chunks = list(chunker.split_text(text, config))

    # Expectations
    # Sentence 1 and 2 merged -> Chunk 0
    # Sentence 3 -> Chunk 1

    assert len(chunks) == 2
    assert "文1" in chunks[0].text
    assert "文2" in chunks[0].text
    assert "文3" not in chunks[0].text

    assert chunks[1].text == "文3。"
    assert chunks[1].index == 1

def test_semantic_chunker_percentile() -> None:
    """Test merging logic with percentile threshold."""
    # Setup
    # 4 sentences
    # Distances: d(0,1)=0.1, d(1,2)=0.9, d(2,3)=0.2
    # Distances array: [0.1, 0.9, 0.2]
    # Percentile 50 -> median distance is 0.2
    # Threshold becomes 0.2
    # d(0,1)=0.1 <= 0.2 -> merge
    # d(1,2)=0.9 > 0.2 -> split
    # d(2,3)=0.2 <= 0.2 -> merge

    # Vectors
    v0 = [1.0, 0.0]
    v1 = [0.99, 0.1] # dist small
    v2 = [0.0, 1.0] # dist large (orthogonal)
    v3 = [0.1, 0.99] # dist small with v2

    mock_embedder = MagicMock()
    mock_embedder.embed_strings.return_value = [v0, v1, v2, v3]

    chunker = JapaneseSemanticChunker(embedder=mock_embedder)

    config = ProcessingConfig(
        chunking=ChunkingConfig(
            semantic_chunking_mode="percentile",
            semantic_chunking_percentile=50
        )
    )

    text = "文1。文2。文3。文4。"

    chunks = list(chunker.split_text(text, config))

    # Check if split happened between 2 and 3 (index 1 and 2 in chunks list terms? No, sentence indices)
    # Sentence 0,1 merged. Sentence 2,3 merged.

    assert len(chunks) == 2
    assert "文1" in chunks[0].text
    assert "文2" in chunks[0].text
    assert "文3" in chunks[1].text
    assert "文4" in chunks[1].text

def test_semantic_chunker_empty() -> None:
    """Test empty input."""
    mock_embedder = MagicMock()
    chunker = JapaneseSemanticChunker(embedder=mock_embedder)
    config = ProcessingConfig()
    chunks = list(chunker.split_text("", config))
    assert len(chunks) == 0

def test_semantic_chunker_single_sentence() -> None:
    """Test single sentence input."""
    mock_embedder = MagicMock()
    v1 = [1.0, 0.0]
    mock_embedder.embed_strings.return_value = [v1]

    chunker = JapaneseSemanticChunker(embedder=mock_embedder)
    config = ProcessingConfig()

    text = "文1。"
    chunks = list(chunker.split_text(text, config))

    assert len(chunks) == 1
    assert chunks[0].text == "文1。"
    assert chunks[0].embedding == v1

def test_semantic_chunker_embedding_failure() -> None:
    """Test behavior when embedding fails."""
    mock_embedder = MagicMock()
    mock_embedder.embed_strings.side_effect = Exception("Embedding failed")

    chunker = JapaneseSemanticChunker(embedder=mock_embedder)
    config = ProcessingConfig()

    text = "文1。文2。"
    # Should handle exception and return empty or raise?
    # Code: logger.exception(...) return iter([])

    chunks = list(chunker.split_text(text, config))
    assert chunks == []
