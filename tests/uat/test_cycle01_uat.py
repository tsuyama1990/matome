import pytest
from domain_models.config import ProcessingConfig
from matome.engines.token_chunker import JapaneseTokenChunker

def test_uat_scenario_04_chunk_size() -> None:
    """
    Scenario 04: Chunk Size Configuration.
    Goal: Verify that changing `max_tokens` affects the chunking output.
    """
    chunker = JapaneseTokenChunker()
    text = "A" * 100  # 100 characters

    # Case 1: Small chunks (10 tokens)
    # Ensure consistency: max_summary_tokens <= max_tokens
    config_small = ProcessingConfig(max_tokens=10, max_summary_tokens=5)
    chunks_small = list(chunker.split_text(text, config_small))

    # Case 2: Large chunks (100 tokens)
    config_large = ProcessingConfig(max_tokens=100, max_summary_tokens=50)
    chunks_large = list(chunker.split_text(text, config_large))

    # Expect more chunks with smaller token limit
    assert len(chunks_small) > len(chunks_large)
