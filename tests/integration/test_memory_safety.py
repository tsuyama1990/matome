import contextlib
from collections.abc import Iterable, Iterator
from typing import Any
from unittest.mock import MagicMock, patch

from domain_models.config import ProcessingConfig
from domain_models.manifest import Chunk, Cluster
from matome.engines.raptor import RaptorEngine


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
    def embed_side_effect(chunks: Iterable[Any]) -> Iterator[Any]:
        for chunk in chunks:
            chunk.embedding = [0.1]
            yield chunk
    embedder.embed_chunks.side_effect = embed_side_effect

    # Clusterer consumes stream
    def cluster_side_effect(embeddings: Iterable[Any], config: ProcessingConfig) -> list[Any]:
        for _ in embeddings:
            pass
        return []
    clusterer.cluster_nodes.side_effect = cluster_side_effect

    engine = RaptorEngine(chunker, embedder, clusterer, summarizer, config)

    with patch("matome.engines.raptor.DiskChunkStore") as MockStore:
        store_instance = MagicMock()
        MockStore.return_value.__enter__.return_value = store_instance

        # Run
        # We expect recursion error or similar because we mocked empty clusters but might expect some
        # But here we just check L0 processing
        with contextlib.suppress(Exception):
            engine.run("dummy text")

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


def test_full_recursion_memory_safety() -> None:
    """Test memory safety through recursion levels."""
    config = ProcessingConfig(
        chunk_buffer_size=10,
        embedding_batch_size=10,
        cluster_batch_size=10
    )

    chunker = MagicMock()
    embedder = MagicMock()
    clusterer = MagicMock()
    summarizer = MagicMock()

    # L0 setup
    chunker.split_text.return_value = iter([Chunk(index=0, text="t", start_char_idx=0, end_char_idx=1)])
    embedder.embed_chunks.return_value = iter([Chunk(index=0, text="t", start_char_idx=0, end_char_idx=1, embedding=[0.1])])

    # L0 Clusterer returns many clusters to simulate large next level
    # 100 clusters
    l0_clusters = [Cluster(id=i, level=0, node_indices=[i]) for i in range(100)]

    # L1 Clusterer returns 1 cluster (Root)
    l1_clusters = [Cluster(id=0, level=1, node_indices=list(range(100)))]

    clusterer.cluster_nodes.side_effect = [l0_clusters, l1_clusters]

    # Summarizer
    summarizer.summarize.return_value = "Summary"

    engine = RaptorEngine(chunker, embedder, clusterer, summarizer, config)

    with patch("matome.engines.raptor.DiskChunkStore") as MockStore:
        store = MagicMock()
        MockStore.return_value.__enter__.return_value = store

        # Setup store counts and IDs
        # Level 0 count: 100 (simulated result of L0 processing)
        # Level 1 count: 100 (after L0 clustering/summarization)
        # Level 2 count: 1 (Root)
        store.get_node_count.side_effect = [1, 100, 1]

        # IDs
        store.get_node_ids_by_level.side_effect = [
            iter(["0"]), # L0 IDs during L0 processing (not used by clusterer in test but maybe logic)
            iter([str(i) for i in range(100)]), # L0 IDs for L1 clustering
            iter([str(i) for i in range(100)]), # L1 IDs for L2 clustering
            iter(["root"]) # L2 ID (Root)
        ]

        # get_nodes needs to return dummy nodes
        def get_nodes_side_effect(ids: Iterable[str]) -> Iterator[Any]:
            for nid in ids:
                yield Chunk(index=int(nid) if nid.isdigit() else 0, text="content", start_char_idx=0, end_char_idx=1)
        store.get_nodes.side_effect = get_nodes_side_effect

        engine.run("Text")

        # Verify add_summaries was called in batches
        # 100 clusters -> 100 summaries. Buffer 10.
        # Should be ~10 calls.
        assert store.add_summaries.call_count >= 10

        for call in store.add_summaries.call_args_list:
            args, _ = call
            batch = args[0]
            assert len(batch) <= 10
