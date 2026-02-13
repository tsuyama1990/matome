from collections.abc import Iterator
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

from domain_models.config import ProcessingConfig
from domain_models.manifest import Chunk, Cluster, DocumentTree, SummaryNode
from matome.engines.raptor import RaptorEngine
from matome.utils.store import DiskChunkStore


def test_raptor_reconstructs_leaf_chunks(tmp_path: Path) -> None:
    """
    Verify that RaptorEngine correctly reconstructs the leaf_chunks list
    and that these chunks are retrievable from the DiskChunkStore.
    """
    # 1. Setup Mocks
    chunker = MagicMock()
    embedder = MagicMock()
    clusterer = MagicMock()
    summarizer = MagicMock()
    config = ProcessingConfig()

    # 2. Setup Data
    # Chunks
    chunks = [
        Chunk(index=0, text="Chunk 0", start_char_idx=0, end_char_idx=10, embedding=[0.1, 0.1]),
        Chunk(index=1, text="Chunk 1", start_char_idx=10, end_char_idx=20, embedding=[0.2, 0.2]),
    ]

    # Chunker returns iterator
    chunker.split_text.return_value = iter(chunks)

    # Embedder returns generator of embeddings
    def embed_gen(chunks_iter: Iterator[Chunk]) -> Iterator[Chunk]:
        for c in chunks_iter:
            if c.embedding is None:
                c.embedding = [0.1, 0.1]
            yield c

    embedder.embed_chunks.side_effect = embed_gen
    embedder.embed_strings.return_value = iter([[0.9, 0.9]])

    # Clusterer returns 1 cluster containing both chunks
    level_0_clusters = [Cluster(id=0, level=0, node_indices=[0, 1])]
    level_1_clusters: list[Cluster] = []

    return_values = [level_0_clusters, level_1_clusters]
    call_count = 0

    def cluster_side_effect(
        embeddings_iter: Iterator[list[float]], config: ProcessingConfig
    ) -> list[Cluster]:
        nonlocal call_count
        _ = list(embeddings_iter) # consume
        result = return_values[call_count]
        call_count += 1
        return result

    clusterer.cluster_nodes.side_effect = cluster_side_effect

    # Summarizer
    def summarize_side_effect(text: str | list[str], context: dict[str, Any] | None = None) -> SummaryNode:
        import uuid
        if context is None:
            context = {}
        return SummaryNode(
            id=context.get("id", str(uuid.uuid4())),
            text="Summary Text",
            level=context.get("level", 1),
            children_indices=context.get("children_indices", []),
            metadata=context.get("metadata", {})
        )
    summarizer.summarize.side_effect = summarize_side_effect

    # 3. Run Engine with Real Store
    store_path = tmp_path / "test.db"
    store = DiskChunkStore(store_path)
    engine = RaptorEngine(chunker, embedder, clusterer, summarizer, config)

    # We must pass the store to run
    tree = engine.run("dummy text", store=store)

    # 4. Assertions
    assert isinstance(tree, DocumentTree)

    # Audit fix: Add assertion to verify tree.leaf_chunk_ids matches expected chunk indices
    expected_ids = [0, 1]
    assert tree.leaf_chunk_ids == expected_ids
    assert len(tree.leaf_chunk_ids) == 2

    # Verify retrieval from store
    chunk0 = store.get_node(0)
    assert isinstance(chunk0, Chunk)
    assert chunk0.text == "Chunk 0"

    store.close()
