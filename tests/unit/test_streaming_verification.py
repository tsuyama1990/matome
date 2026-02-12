from collections.abc import Iterator
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from domain_models.config import ProcessingConfig
from domain_models.manifest import Chunk, Cluster, DocumentTree
from matome.engines.raptor import RaptorEngine


def test_raptor_reconstructs_leaf_chunks(tmp_path: Path) -> None:
    """
    Verify that RaptorEngine correctly reconstructs the leaf_chunks list
    from the DiskChunkStore at the end of the pipeline.
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
    # Note: embedder.embed_chunks receives the iterator from chunker.
    # It must yield chunks with embeddings.
    def embed_gen(chunks_iter: "Iterator[Chunk]") -> "Iterator[Chunk]":
        for c in chunks_iter:
            # Check if embedding is present (it is in our data), else set it
            if c.embedding is None:
                c.embedding = [0.1, 0.1]
            yield c

    embedder.embed_chunks.side_effect = embed_gen

    # Embedder string support for summaries (root node embedding)
    embedder.embed_strings.return_value = iter([[0.9, 0.9]])

    # Clusterer returns 1 cluster containing both chunks (Level 0 -> Level 1)
    # IMPORTANT: The mock must consume the input generator to trigger the side effects
    # in RaptorEngine (saving to store, populating ids).

    # We define a side effect for cluster_nodes that consumes the generator

    level_0_clusters = [Cluster(id=0, level=0, node_indices=[0, 1])]
    level_1_clusters: list[Cluster] = []  # Stop condition

    return_values = [level_0_clusters, level_1_clusters]
    call_count = 0

    def cluster_side_effect(
        embeddings_iter: "Iterator[list[float]]", config: ProcessingConfig
    ) -> list[Cluster]:
        nonlocal call_count
        # Consume the generator!
        _ = list(embeddings_iter)

        result = return_values[call_count]
        call_count += 1
        return result

    clusterer.cluster_nodes.side_effect = cluster_side_effect

    # Summarizer
    def summarize_side_effect(text, context=None):
        import uuid
        from domain_models.manifest import SummaryNode
        return SummaryNode(
            id=context.get("id", str(uuid.uuid4())),
            text="Summary Text",
            level=context.get("level", 1),
            children_indices=context.get("children_indices", []),
            metadata=context.get("metadata", {})
        )
    summarizer.summarize.side_effect = summarize_side_effect

    # 3. Run Engine
    engine = RaptorEngine(chunker, embedder, clusterer, summarizer, config)

    tree = engine.run("dummy text")

    # 4. Assertions
    assert isinstance(tree, DocumentTree)

    # Verify leaf_chunk_ids are populated
    assert len(tree.leaf_chunk_ids) == 2

    # Verify IDs match
    assert set(tree.leaf_chunk_ids) == {0, 1}

    # Note: Text is not in the tree anymore, would need to fetch from store.

    # Verify structure
    assert tree.root_node.text == "Summary Text"
    # The summary node children indices should correspond to the L0 IDs.
    # checking that children_indices contains 0 and 1
    assert set(tree.root_node.children_indices) == {0, 1}


def test_raptor_empty_iterator_error() -> None:
    """Verify error handling when chunker yields nothing."""
    chunker = MagicMock()
    chunker.split_text.return_value = iter([])  # Empty

    clusterer = MagicMock()
    # If empty, clusterer might be called with empty generator.
    clusterer.cluster_nodes.return_value = []

    engine = RaptorEngine(
        chunker=chunker,
        embedder=MagicMock(),
        clusterer=clusterer,
        summarizer=MagicMock(),
        config=ProcessingConfig(),
    )

    # Should likely raise ValueError or return empty tree depending on implementation.
    # Implementation says: if node_count == 0 pass, then _finalize_tree checks if current_level_ids is empty.

    with pytest.raises(ValueError, match="No nodes remaining"):
        engine.run("empty")
