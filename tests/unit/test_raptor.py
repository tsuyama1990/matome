from collections.abc import Iterator
from unittest.mock import MagicMock

import pytest

from domain_models.config import ProcessingConfig
from domain_models.manifest import Chunk, Cluster, DocumentTree
from matome.engines.raptor import RaptorEngine


@pytest.fixture
def mock_dependencies() -> tuple[MagicMock, MagicMock, MagicMock, MagicMock]:
    chunker = MagicMock()
    embedder = MagicMock()
    clusterer = MagicMock()
    summarizer = MagicMock()
    return chunker, embedder, clusterer, summarizer

@pytest.fixture
def config() -> ProcessingConfig:
    return ProcessingConfig()

def test_raptor_initialization(mock_dependencies: tuple[MagicMock, ...], config: ProcessingConfig) -> None:
    chunker, embedder, clusterer, summarizer = mock_dependencies
    engine = RaptorEngine(
        chunker=chunker,
        embedder=embedder,
        clusterer=clusterer,
        summarizer=summarizer,
        config=config
    )
    assert engine.chunker == chunker
    assert engine.embedder == embedder
    assert engine.clusterer == clusterer
    assert engine.summarizer == summarizer

def test_raptor_run_short_text(mock_dependencies: tuple[MagicMock, ...], config: ProcessingConfig) -> None:
    """Test processing a short text that results in a single level of summarization."""
    chunker, embedder, clusterer, summarizer = mock_dependencies
    engine = RaptorEngine(chunker, embedder, clusterer, summarizer, config)

    # 1. Chunking returns 1 chunk
    chunk1 = Chunk(index=0, text="Short text", start_char_idx=0, end_char_idx=10)
    chunker.split_text.return_value = [chunk1]

    # 2. Embedding
    # embedder.embed_chunks returns an iterator yielding chunks with embeddings
    # We must ensure that the side_effect returns an iterable, AND modifies the chunks.
    # The engine consumes the iterator.
    def side_effect_embed_chunks_gen(chunks: list[Chunk]) -> Iterator[Chunk]:
        for c in chunks:
            c.embedding = [0.1, 0.2]
            yield c

    embedder.embed_chunks.side_effect = side_effect_embed_chunks_gen

    # 3. Clustering
    # Should NOT be called because len(chunks) == 1, so node_count=1 -> break loop.

    # 4. Summarization
    # Not called.

    # Run
    tree = engine.run("Short text")

    # Verify
    embedder.embed_chunks.assert_called_once()
    clusterer.cluster_nodes.assert_not_called()
    summarizer.summarize.assert_not_called()

    assert isinstance(tree, DocumentTree)
    assert len(tree.leaf_chunks) == 1
    # Since loop broke immediately, it enters _finalize_root.
    # Single chunk -> Wrapped in SummaryNode.
    assert tree.root_node.level == 1
    # text should be chunk text because we wrap it.
    assert tree.root_node.text == "Short text"
    assert tree.root_node.children_indices == [0] # Points to chunk index 0
    assert len(tree.all_nodes) == 1 # Only root node

def test_raptor_run_recursive(mock_dependencies: tuple[MagicMock, ...], config: ProcessingConfig) -> None:
    """Test processing text that requires multiple levels of summarization."""
    chunker, embedder, clusterer, summarizer = mock_dependencies
    engine = RaptorEngine(chunker, embedder, clusterer, summarizer, config)

    # Level 0: 3 Chunks
    chunks = [
        Chunk(index=i, text=f"Chunk {i}", start_char_idx=i*10, end_char_idx=(i+1)*10)
        for i in range(3)
    ]
    chunker.split_text.return_value = chunks

    # Mock embedding to always populate embedding field
    def side_effect_embed_chunks(chunks: list[Chunk]) -> Iterator[Chunk]:
        for c in chunks:
            c.embedding = [0.1] * 768
            yield c
    embedder.embed_chunks.side_effect = side_effect_embed_chunks

    # Mock embedding for summary nodes (strings)
    embedder.embed_strings.return_value = [[0.2] * 768] # For any summary

    # Clustering Logic
    # Call 1 (Level 0 Chunks): Returns 2 clusters (needs reducing)
    # Cluster 0: [0, 1], Cluster 1: [2]
    cluster_l0_0 = Cluster(id=0, level=0, node_indices=[0, 1])
    cluster_l0_1 = Cluster(id=1, level=0, node_indices=[2])

    # Call 2 (Level 1 Summaries): Returns 1 cluster (Root)
    # Cluster 0: [0, 1] (Indices into the list of summaries from L0 clusters)
    cluster_l1_0 = Cluster(id=0, level=1, node_indices=[0, 1]) # Summaries of c0 and c1

    clusterer.cluster_nodes.side_effect = [
        [cluster_l0_0, cluster_l0_1], # First pass
        [cluster_l1_0]                # Second pass
    ]

    # Summarization
    summarizer.summarize.side_effect = [
        "Summary L1-0", # Summary of Cluster L0-0
        "Summary L1-1", # Summary of Cluster L0-1
        "Root Summary"  # Summary of Cluster L1-0
    ]

    # Run
    tree = engine.run("Long text")

    # Verify
    assert isinstance(tree, DocumentTree)
    assert tree.root_node.text == "Root Summary"
    assert tree.root_node.level == 2 # L0 -> L1 -> L2 (Root)

    # Check L1 nodes
    root_children_ids = tree.root_node.children_indices
    assert len(root_children_ids) == 2
    assert all(isinstance(uid, str) for uid in root_children_ids)

    # Verify we have all nodes
    # Root + 2 L1 nodes = 3 nodes
    assert len(tree.all_nodes) == 3
