from unittest.mock import MagicMock, patch

import pytest

from domain_models.manifest import Chunk
from matome.engines.embedder import EmbeddingService


@pytest.fixture
def sample_chunks():
    return [
        Chunk(index=0, text="Hello world", start_char_idx=0, end_char_idx=11),
        Chunk(index=1, text="Test sentence", start_char_idx=12, end_char_idx=25)
    ]

@patch("matome.engines.embedder.SentenceTransformer")
def test_embed_chunks(mock_st_cls, sample_chunks) -> None:
    # Mock the instance returned by SentenceTransformer()
    mock_instance = MagicMock()
    mock_st_cls.return_value = mock_instance

    # Mock encode method
    import numpy as np
    mock_instance.encode.return_value = np.array([
        [0.1] * 1024,
        [0.2] * 1024
    ])

    service = EmbeddingService(model_name="test-model")
    chunks = service.embed_chunks(sample_chunks)

    # Check if chunks have embeddings
    assert len(chunks) == 2
    assert chunks[0].embedding == [0.1] * 1024
    assert chunks[1].embedding == [0.2] * 1024

    # Verify calls
    mock_st_cls.assert_called_with("test-model")
    mock_instance.encode.assert_called_once()
    args, kwargs = mock_instance.encode.call_args
    assert args[0] == ["Hello world", "Test sentence"]
    assert kwargs.get('convert_to_numpy') is True
