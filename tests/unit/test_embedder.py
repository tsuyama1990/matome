from unittest.mock import MagicMock, patch

import numpy as np

from domain_models.config import ProcessingConfig
from domain_models.manifest import Chunk
from matome.engines.embedder import EmbeddingService


# Scenario 05: Embedding Vector Generation
def test_scenario_05_embedding_vector_generation() -> None:
    chunks = [
        Chunk(index=0, text="This is a test.", start_char_idx=0, end_char_idx=15),
        Chunk(index=1, text="Another sentence.", start_char_idx=16, end_char_idx=33),
    ]

    with patch("matome.engines.embedder.SentenceTransformer") as mock_st:
        mock_instance = MagicMock()
        mock_st.return_value = mock_instance
        # Use small vector dimension (32) to save memory in tests
        # Mock encode to return a list of arrays (simulating convert_to_numpy=True)
        # Note: embed_strings yields a generator, embed_chunks consumes it
        mock_instance.encode.return_value = np.array([
            list(np.random.rand(32)),
            list(np.random.rand(32))
        ])

        config = ProcessingConfig()
        service = EmbeddingService(config)
        embedded_chunks = service.embed_chunks(chunks)

        for chunk in embedded_chunks:
            assert chunk.embedding is not None
            assert len(chunk.embedding) == 32

def test_embed_strings_generator() -> None:
    texts = ["text1", "text2", "text3"]
    config = ProcessingConfig(embedding_batch_size=2)

    with patch("matome.engines.embedder.SentenceTransformer") as mock_st:
        mock_instance = MagicMock()
        mock_st.return_value = mock_instance
        # 1st batch (2 items)
        # 2nd batch (1 item)
        mock_instance.encode.side_effect = [
            np.array([[0.1, 0.1], [0.2, 0.2]]),
            np.array([[0.3, 0.3]])
        ]

        # Instantiate inside the patch to use the mock
        service = EmbeddingService(config)

        embeddings_gen = service.embed_strings(texts)

        # Consuming the generator
        results = list(embeddings_gen)

        assert len(results) == 3
        # Use numpy testing for float comparison
        np.testing.assert_allclose(results[0], [0.1, 0.1], atol=1e-5)
        np.testing.assert_allclose(results[1], [0.2, 0.2], atol=1e-5)
        np.testing.assert_allclose(results[2], [0.3, 0.3], atol=1e-5)

        # Verify batching calls
        assert mock_instance.encode.call_count == 2
        # Note: check arguments carefully.
        # The first call should be with the first batch
        mock_instance.encode.assert_any_call(["text1", "text2"], batch_size=2, convert_to_numpy=True, show_progress_bar=False)
        # The second call with the remainder
        mock_instance.encode.assert_any_call(["text3"], batch_size=1, convert_to_numpy=True, show_progress_bar=False)

def test_embed_strings_empty() -> None:
    config = ProcessingConfig()

    # Mock model not even loaded or called
    with patch("matome.engines.embedder.SentenceTransformer") as mock_st:
        service = EmbeddingService(config)
        results = list(service.embed_strings([]))
        assert results == []
        # Encode should not be called
        mock_st.return_value.encode.assert_not_called()
