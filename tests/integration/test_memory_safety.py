from unittest.mock import MagicMock, patch

import pytest

from domain_models.config import ProcessingConfig
from matome.engines.raptor import RaptorEngine
from matome.utils.store import DiskChunkStore


def test_memory_safety_streaming() -> None:
    """
    Simulate a large-scale processing run to verify memory safety.
    Uses mocks to ensure we don't actually process 100k items,
    but we verify that the pipeline processes them in batches.
    """
    config = ProcessingConfig(
        chunk_buffer_size=10, # Small buffer to force many flushes
        embedding_batch_size=10,
        write_batch_size=10
    )

    # Mock dependencies
    chunker = MagicMock()
    embedder = MagicMock()
    clusterer = MagicMock()
    summarizer = MagicMock()

    # Create a large stream of fake chunks
    TOTAL_ITEMS = 1000
    fake_chunks = (MagicMock(index=i, text=f"Chunk {i}", embedding=[0.1]) for i in range(TOTAL_ITEMS))

    chunker.split_text.return_value = fake_chunks

    # Embedder must pass through the stream
    def embed_side_effect(chunks):
        for chunk in chunks:
            chunk.embedding = [0.1]
            yield chunk
    embedder.embed_chunks.side_effect = embed_side_effect

    # Clusterer consumes stream
    def cluster_side_effect(embeddings, config):
        for _ in embeddings:
            pass
        return []
    clusterer.cluster_nodes.side_effect = cluster_side_effect

    engine = RaptorEngine(chunker, embedder, clusterer, summarizer, config)

    with patch("matome.engines.raptor.DiskChunkStore") as MockStore:
        store_instance = MagicMock()
        MockStore.return_value.__enter__.return_value = store_instance

        # Run
        try:
            engine.run("dummy text")
        except Exception:
            # We expect recursion error or similar because we mocked empty clusters but might expect some
            # But here we just check L0 processing
            pass

        # Verify L0 added chunks in batches
        # Total items 1000, buffer 10 -> 100 calls to add_chunks
        # The number of calls might differ if implementation logic varies (e.g. initial flush etc)
        # But should be around 100
        assert store_instance.add_chunks.call_count == 100

        # Verify we didn't load all 1000 into one call
        for call in store_instance.add_chunks.call_args_list:
            args, _ = call
            batch = args[0]
            assert len(batch) <= 10 # Should be exactly 10 mostly
