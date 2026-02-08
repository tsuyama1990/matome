from collections.abc import Iterator
from pathlib import Path

from domain_models.config import ProcessingConfig
from matome.engines.chunker import JapaneseTokenChunker
from matome.utils.io import read_file
from matome.utils.text import normalize_text


def stream_file(filepath: Path) -> Iterator[str]:
    """Yield lines from file."""
    with filepath.open("r", encoding="utf-8") as f:
        yield from f

def test_chunking_pipeline_integration() -> None:
    """
    Integration test for the chunking pipeline.
    Reads a real Japanese text file using streaming, chunks it, and verifies the output.
    """
    # Setup
    sample_file = Path("tests/data/sample_jp.txt")

    # Ensure the file exists (it might be missing in the environment)
    if not sample_file.exists():
        # Create a dummy file if it doesn't exist for testing purposes
        sample_file.parent.mkdir(parents=True, exist_ok=True)
        sample_file.write_text("これはテストです。日本語の文章です。\nRAPTORシステムをテストします。\nLost-in-the-Middle問題を解決します。", encoding="utf-8")

    # For verification, we read the whole file (assuming it's small enough for test assertion)
    full_text = read_file(sample_file)
    normalized_input = normalize_text(full_text)

    chunker = JapaneseTokenChunker()
    # Use high_precision factory which sets max_tokens=200
    config = ProcessingConfig.high_precision()

    # Execute using stream
    # This proves the chunker can handle iterables (scalability requirement)
    chunks = chunker.split_text(stream_file(sample_file), config)

    # Verify
    assert len(chunks) > 0
    assert chunks[0].index == 0

    reconstructed = ""
    current_idx = 0

    for i, chunk in enumerate(chunks):
        # 1. Sequential Index Check
        assert chunk.index == i

        # 2. Start/End Index Check
        # start_char_idx should match the cumulative length so far
        assert chunk.start_char_idx == current_idx
        # end_char_idx should be start + length
        expected_end = current_idx + len(chunk.text)
        assert chunk.end_char_idx == expected_end

        reconstructed += chunk.text
        current_idx = expected_end

        # 3. Token Limit Check (Approximate)
        assert len(chunk.text) < 1000

    # 4. Content Preservation Check
    # We compare cleaned versions because sentence splitting consumes newlines/whitespace
    reconstructed_clean = reconstructed.replace("\n", "").replace(" ", "").replace("　", "")
    original_clean = normalized_input.replace("\n", "").replace(" ", "").replace("　", "")

    assert reconstructed_clean == original_clean

    # Key phrases check
    assert "Lost-in-the-Middle" in reconstructed
    assert "RAPTOR" in reconstructed
    assert "日本語" in reconstructed
