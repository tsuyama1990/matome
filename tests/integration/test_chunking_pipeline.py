from pathlib import Path
from unittest.mock import MagicMock, patch

from domain_models.config import ProcessingConfig
from matome.engines.token_chunker import JapaneseTokenChunker
from matome.utils.text import normalize_text


def test_chunking_pipeline_integration(tmp_path: Path) -> None:
    """
    Integration test for the chunking pipeline.
    Uses mock file I/O to avoid disk dependency issues during testing.
    """
    # Setup
    content = "これはテストです。日本語の文章です。RAPTORシステムをテストします。Lost-in-the-Middle問題を解決します。"

    # Mock read_file to simulate reading from disk if we used it,
    # but more importantly, mock the tokenizer to avoid network/hashing issues in restricted envs.
    with patch("matome.engines.token_chunker.get_cached_tokenizer") as mock_get_tokenizer:
        # Mock tokenizer behavior
        mock_tokenizer = MagicMock()
        # Simple mock: 1 char = 1 token for simplicity in testing logic
        mock_tokenizer.encode.side_effect = lambda text: [ord(c) for c in text]
        mock_get_tokenizer.return_value = mock_tokenizer

        text = content
        normalized_input = normalize_text(text)

        chunker = JapaneseTokenChunker()
        # Use a small token limit to force multiple chunks.
        # With mock tokenizer (1 char = 1 token), 50 tokens is enough for the long sentence (27 chars).
        config = ProcessingConfig(max_tokens=50, overlap=0)

        # Execute
        chunks = list(chunker.split_text(text, config))

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

            # 3. Token Limit Check (Strict)
            # count_tokens uses self.tokenizer.encode, which we mocked
            token_count = chunker.count_tokens(chunk.text)
            assert token_count <= config.max_tokens, (
                f"Chunk {i} exceeds max tokens: {token_count} > {config.max_tokens}"
            )

        # 4. Content Preservation Check
        # Verify reconstructed text matches normalized input (ignoring whitespace differences caused by splitting)
        reconstructed_clean = reconstructed.replace("\n", "").replace(" ", "").replace("　", "")
        original_clean = normalized_input.replace("\n", "").replace(" ", "").replace("　", "")

        assert reconstructed_clean == original_clean

        # Key phrases check
        assert "Lost-in-the-Middle" in reconstructed
        assert "RAPTOR" in reconstructed
        assert "日本語" in reconstructed


def test_chunking_edge_cases() -> None:
    """Test chunking with edge cases like empty input and large text."""
    # Empty input
    # Need to mock tokenizer even for empty init if it loads model
    with patch("matome.engines.token_chunker.get_cached_tokenizer") as mock_get_tokenizer:
        mock_tokenizer = MagicMock()
        mock_get_tokenizer.return_value = mock_tokenizer

        chunker = JapaneseTokenChunker()
        config = ProcessingConfig()
        chunks = list(chunker.split_text("", config))
        assert len(chunks) == 0

    # Large text with punctuations to ensure sentence splitting works
    # 20 sentences of 500 chars each (499 + 1 punctuation)
    large_text = ("あ" * 499 + "。") * 20

    with patch("matome.engines.token_chunker.get_cached_tokenizer") as mock_get_tokenizer:
        mock_tokenizer = MagicMock()
        # Mock encoding: 1 char = 1 token
        mock_tokenizer.encode.side_effect = lambda text: [1] * len(text)
        mock_tokenizer.name = "mock_model"
        mock_get_tokenizer.return_value = mock_tokenizer

        chunker = JapaneseTokenChunker()
        config = ProcessingConfig(max_tokens=500, overlap=0)

        chunks = list(chunker.split_text(large_text, config))
        # 20 sentences * 500 tokens / 500 max = 20 chunks
        assert len(chunks) == 20
