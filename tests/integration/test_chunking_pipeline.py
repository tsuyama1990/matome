import tempfile
from pathlib import Path

from matome.engines.token_chunker import JapaneseTokenChunker
from matome.utils.text import normalize_text
from domain_models.config import ProcessingConfig

def test_chunking_pipeline_integration() -> None:
    """
    Integration test for text normalization and chunking.
    Verifies that text flows correctly from raw string to normalized tokens to chunks.
    """
    # Create a dummy Japanese text file
    content = "これはテストです。文書を分割し、クラスタリングし、要約します。" * 5

    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", delete=False) as f:
        f.write(content)
        temp_path = Path(f.name)

    try:
        with open(temp_path, "r", encoding="utf-8") as f:
            text = f.read()

        normalized_input = normalize_text(text)

        chunker = JapaneseTokenChunker()
        # Use a small token limit to force multiple chunks.
        # With mock tokenizer (1 char = 1 token), 50 tokens is enough for the long sentence (27 chars).
        # Fix: max_summary_tokens must be <= max_tokens
        config = ProcessingConfig(max_tokens=50, max_summary_tokens=20, overlap=0)

        chunks = list(chunker.split_text(normalized_input, config))

        assert len(chunks) > 1
        assert chunks[0].index == 0
        assert chunks[1].index == 1

        # Verify text content roughly
        assert "これ" in chunks[0].text

    finally:
        temp_path.unlink()
