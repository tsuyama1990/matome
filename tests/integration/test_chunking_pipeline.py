import pytest
from domain_models.config import ProcessingConfig
from domain_models.manifest import Chunk
from matome.engines.token_chunker import JapaneseTokenChunker, TokenChunker

def test_chunking_pipeline_integration() -> None:
    """
    Test the chunking pipeline with real engines (JapaneseTokenChunker).
    """
    config = ProcessingConfig(max_tokens=10, overlap=0)
    chunker = JapaneseTokenChunker()
    text = "これはテストです。短い文。"

    # split_text returns an iterator
    chunks = list(chunker.split_text(text, config))

    assert len(chunks) > 0
    assert isinstance(chunks[0], Chunk)
    assert chunks[0].index == 0
