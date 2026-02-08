from unittest.mock import MagicMock, patch

import pytest

from domain_models.config import EmbeddingConfig, ProcessingConfig
from domain_models.manifest import Chunk
from matome.engines.embedder import EmbeddingService


@pytest.fixture
def sample_chunks() -> list[Chunk]:
    return [
        Chunk(index=0, text="Hello world", start_char_idx=0, end_char_idx=11),
        Chunk(index=1, text="Test sentence", start_char_idx=12, end_char_idx=25)
    ]

@patch("matome.engines.embedder.SentenceTransformer")
def test_embed_chunks(mock_st_cls: MagicMock, sample_chunks: list[Chunk]) -> None:
    # Mock the instance returned by SentenceTransformer()
    mock_instance = MagicMock()
    mock_st_cls.return_value = mock_instance

    # Mock encode method
    import numpy as np
    mock_instance.encode.return_value = np.array([
        [0.1] * 1024,
        [0.2] * 1024
    ])

    config = ProcessingConfig(embedding=EmbeddingConfig(model_name="test-model", batch_size=2))
    service = EmbeddingService(config)

    # Process generator
    chunk_iterator = service.embed_chunks(iter(sample_chunks))
    processed_chunks = list(chunk_iterator)

    # Check if chunks have embeddings
    assert len(processed_chunks) == 2
    assert processed_chunks[0].embedding == [0.1] * 1024
    assert processed_chunks[1].embedding == [0.2] * 1024

    # Verify calls
    mock_st_cls.assert_called_with("test-model")
    mock_instance.encode.assert_called_once()

    # Check arguments: should have batch_size
    args, kwargs = mock_instance.encode.call_args
    assert args[0] == ["Hello world", "Test sentence"]
    assert kwargs.get('batch_size') == 2
    assert kwargs.get('convert_to_numpy') is True

@patch("matome.engines.embedder.SentenceTransformer")
def test_embed_chunks_batching(mock_st_cls: MagicMock) -> None:
    """Test that embedding processes in correct batch sizes."""
    mock_instance = MagicMock()
    mock_st_cls.return_value = mock_instance
    import numpy as np

    # Setup for 3 chunks with batch_size=2
    # First call gets 2 chunks, second gets 1 chunk
    mock_instance.encode.side_effect = [
        np.array([[0.1]*10, [0.2]*10]),
        np.array([[0.3]*10])
    ]

    chunks = [
        Chunk(index=0, text="A", start_char_idx=0, end_char_idx=1),
        Chunk(index=1, text="B", start_char_idx=2, end_char_idx=3),
        Chunk(index=2, text="C", start_char_idx=4, end_char_idx=5),
    ]

    config = ProcessingConfig(embedding=EmbeddingConfig(batch_size=2))
    service = EmbeddingService(config)

    processed = list(service.embed_chunks(iter(chunks)))

    assert len(processed) == 3
    assert mock_instance.encode.call_count == 2

    # Check batch calls
    call_args_list = mock_instance.encode.call_args_list
    assert call_args_list[0][0][0] == ["A", "B"]
    assert call_args_list[1][0][0] == ["C"]
