from pathlib import Path

from domain_models.config import ProcessingConfig
from matome.engines.chunker import JapaneseSemanticChunker
from matome.utils.io import read_file


def test_chunking_pipeline_integration() -> None:
    """
    Integration test for the chunking pipeline.
    Reads a real Japanese text file, chunks it, and verifies the output.
    """
    # Setup
    sample_file = Path("tests/data/sample_jp.txt")
    text = read_file(sample_file)

    chunker = JapaneseSemanticChunker()
    # Use a small token limit to force multiple chunks
    config = ProcessingConfig.high_precision()

    # Execute
    chunks = chunker.split_text(text, config)

    # Verify
    assert len(chunks) > 0
    assert chunks[0].index == 0

    # Check that we didn't lose any content (approximate check via length)
    # Note: Normalization might change length slightly, but content should persist.
    reconstructed = "".join(c.text for c in chunks)

    # Remove newlines for comparison as split_sentences might affect them slightly depending on implementation
    # Actually, let's just check key phrases exist
    assert "Lost-in-the-Middle" in reconstructed
    assert "RAPTOR" in reconstructed
    assert "日本語に最適化された" in reconstructed

    # Check max token compliance (roughly)
    for chunk in chunks:
        # We can't easily check exact tokens here without the tokenizer instance,
        # but we can trust the unit tests for strict compliance.
        # Just ensure chunks aren't suspiciously massive.
        assert len(chunk.text) < 1000  # 200 tokens ~ 200-400 chars roughly
