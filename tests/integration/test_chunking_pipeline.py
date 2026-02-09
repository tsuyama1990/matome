from pathlib import Path

from domain_models.config import ProcessingConfig
from matome.engines.token_chunker import JapaneseTokenChunker
from matome.utils.io import read_file
from matome.utils.text import normalize_text


def test_chunking_pipeline_integration(tmp_path: Path) -> None:
    """
    Integration test for the chunking pipeline.
    Reads a real Japanese text file, chunks it, and verifies the output.
    """
    # Setup
    sample_file = tmp_path / "sample_jp.txt"
    sample_file.write_text(
        "これはテストです。日本語の文章です。RAPTORシステムをテストします。Lost-in-the-Middle問題を解決します。",
        encoding="utf-8",
    )

    text = read_file(sample_file)
    normalized_input = normalize_text(text)

    chunker = JapaneseTokenChunker()
    # Use a small token limit to force multiple chunks, explicit overlap=0 as implementation doesn't support overlap yet
    config = ProcessingConfig(max_tokens=50, overlap=0)

    # Execute
    chunks = chunker.split_text(text, config)

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
        token_count = chunker.count_tokens(chunk.text)
        assert token_count <= config.max_tokens, f"Chunk {i} exceeds max tokens: {token_count} > {config.max_tokens}"

    # 4. Content Preservation Check
    # The concatenated chunks should exactly match the normalized input text
    # (since the chunker normalizes before splitting)
    # Note: split_sentences removes empty strings, but our input text shouldn't have gaps if normalize_text handles it.
    # However, split_sentences splits by regex which might consume delimiters depending on implementation.
    # The implementation uses regex lookbehind `(?<=[。！？])` so it keeps punctuation.
    # It also splits on `\n+`. If the original text had newlines, split_sentences *consumes* them if they are separators?
    # Let's check `split_sentences` logic.
    # It splits on `(?<=[。！？])\s*|\n+`.
    # `\s*` means whitespace after punctuation is consumed.
    # `\n+` means newlines are consumed.
    # So `"".join(chunks)` will effectively lose newlines and some whitespace.
    # Therefore, we can't assert strict equality with `normalized_input` unless we strip those from `normalized_input` too.

    # Let's verify that the *reconstructed text* is contained in *normalized_input*
    # (meaning we didn't add anything), and that key content is present.
    # Actually, a better check is if we remove all whitespace/newlines from both, they match?

    reconstructed_clean = reconstructed.replace("\n", "").replace(" ", "").replace("　", "")
    original_clean = normalized_input.replace("\n", "").replace(" ", "").replace("　", "")

    assert reconstructed_clean == original_clean

    # Key phrases check
    assert "Lost-in-the-Middle" in reconstructed
    assert "RAPTOR" in reconstructed
    assert "日本語" in reconstructed
