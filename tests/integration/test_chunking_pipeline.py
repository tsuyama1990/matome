from collections.abc import Iterator
from pathlib import Path

from domain_models.config import ProcessingConfig, ChunkingConfig
from matome.engines.chunker import JapaneseTokenChunker
from matome.utils.text import normalize_text


def stream_file(filepath: Path) -> Iterator[str]:
    """Yield lines from file."""
    with filepath.open("r", encoding="utf-8") as f:
        yield from f

def test_chunking_pipeline_integration() -> None:
    """
    Integration test for the chunking pipeline.
    Reads a real Japanese text file using streaming, chunks it, and verifies the output.
    Crucially, it never loads the full file content into memory at once.
    """
    # Setup
    sample_file = Path("tests/data/sample_jp.txt")

    # Ensure the file exists (it might be missing in the environment)
    if not sample_file.exists():
        # Create a dummy file if it doesn't exist for testing purposes
        sample_file.parent.mkdir(parents=True, exist_ok=True)
        sample_file.write_text("これはテストです。日本語の文章です。\nRAPTORシステムをテストします。\nLost-in-the-Middle問題を解決します。", encoding="utf-8")

    # We do NOT read the full file for comparison to avoid memory violation.
    # Instead, we verify properties of the chunks and perhaps specific content we know exists.

    chunker = JapaneseTokenChunker()
    # Use high_precision factory which sets max_tokens=200
    config = ProcessingConfig.high_precision()

    # Execute using stream
    # This proves the chunker can handle iterables (scalability requirement)
    chunk_iterator = chunker.split_text(stream_file(sample_file), config)

    # Verify without loading everything to list if possible, or just consume linearly

    reconstructed_len = 0
    current_idx = 0
    found_phrases = {
        "Lost-in-the-Middle": False,
        "RAPTOR": False,
        "日本語": False
    }

    count = 0
    for chunk in chunk_iterator:
        count += 1
        # 1. Sequential Index Check
        assert chunk.index == count - 1 # indices are 0-based

        # 2. Start/End Index Check
        # start_char_idx should match the cumulative length so far
        assert chunk.start_char_idx == current_idx
        # end_char_idx should be start + length
        expected_end = current_idx + len(chunk.text)
        assert chunk.end_char_idx == expected_end

        reconstructed_len += len(chunk.text)
        current_idx = expected_end

        # 3. Token Limit Check (Approximate)
        # We assert each chunk is reasonable size
        assert len(chunk.text) < 1000

        # 4. Phrase Check
        for phrase in found_phrases:
            if phrase in chunk.text:
                found_phrases[phrase] = True

    assert count > 0
    assert all(found_phrases.values()), f"Missing phrases: {found_phrases}"
