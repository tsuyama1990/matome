import uuid
from collections.abc import Iterator
from typing import Any
from unittest.mock import MagicMock, create_autospec

import pytest

from domain_models.config import ProcessingConfig
from domain_models.manifest import Chunk, Cluster, DocumentTree, SummaryNode
from matome.engines.embedder import EmbeddingService
from matome.engines.raptor import RaptorEngine
from matome.interfaces import Chunker, Clusterer, Summarizer


@pytest.fixture
def mock_dependencies() -> tuple[MagicMock, MagicMock, MagicMock, MagicMock]:
    chunker = create_autospec(Chunker, instance=True)
    embedder = create_autospec(EmbeddingService, instance=True)
    clusterer = create_autospec(Clusterer, instance=True)
    summarizer = create_autospec(Summarizer, instance=True)
    return chunker, embedder, clusterer, summarizer


@pytest.fixture
def config() -> ProcessingConfig:
    return ProcessingConfig()


def test_raptor_initialization(
    mock_dependencies: tuple[MagicMock, ...], config: ProcessingConfig
) -> None:
    chunker, embedder, clusterer, summarizer = mock_dependencies
    engine = RaptorEngine(
        chunker=chunker,
        embedder=embedder,
        clusterer=clusterer,
        summarizer=summarizer,
        config=config,
    )
    assert engine.chunker == chunker
    assert engine.embedder == embedder
    assert engine.clusterer == clusterer
    assert engine.summarizer == summarizer


def test_raptor_run_short_text(
    mock_dependencies: tuple[MagicMock, ...], config: ProcessingConfig
) -> None:
    """Test processing a short text that results in a single level of summarization."""
    chunker, embedder, clusterer, summarizer = mock_dependencies
    engine = RaptorEngine(chunker, embedder, clusterer, summarizer, config)

    # 1. Chunking returns 1 chunk
    chunk1 = Chunk(index=0, text="Short text", start_char_idx=0, end_char_idx=10)
    chunker.split_text.return_value = iter([chunk1])

    # 2. Embedding
    # We must ensure embed_chunks works even for single chunk
    chunk1.embedding = [0.1] * 768
    embedder.embed_chunks.return_value = iter([chunk1])

    # IMPORTANT: Mock clusterer to consume the generator
    # Even for 1 chunk, cluster_nodes is called to consume stream
    def side_effect_cluster(
        embeddings: Iterator[list[float]], config: ProcessingConfig
    ) -> list[Cluster]:
        # Consume
        count = sum(1 for _ in embeddings)
        if count <= 1:
            # GMMClusterer returns 1 cluster for 1 item edge case
            # Indices are 0-based relative to the batch.
            return [Cluster(id=0, level=0, node_indices=[0])] if count == 1 else []
        return []

    clusterer.cluster_nodes.side_effect = side_effect_cluster

    # Run
    tree = engine.run("Short text")

    # Verify
    embedder.embed_chunks.assert_called()
    clusterer.cluster_nodes.assert_called()
    summarizer.summarize.assert_not_called()

    assert isinstance(tree, DocumentTree)
    assert len(tree.leaf_chunk_ids) == 1
    assert tree.root_node.level == 1
    assert tree.root_node.text == "Short text"
    assert tree.root_node.children_indices == [0]
    assert len(tree.all_nodes) == 1


def test_raptor_run_recursive(
    mock_dependencies: tuple[MagicMock, ...], config: ProcessingConfig
) -> None:
    """Test processing text that requires multiple levels of summarization."""
    chunker, embedder, clusterer, summarizer = mock_dependencies
    engine = RaptorEngine(chunker, embedder, clusterer, summarizer, config)

    # Level 0: 3 Chunks
    chunks = [
        Chunk(index=i, text=f"Chunk {i}", start_char_idx=i * 10, end_char_idx=(i + 1) * 10)
        for i in range(3)
    ]
    chunker.split_text.return_value = iter(chunks)

    # Mock embedding to always populate embedding field
    def side_effect_embed_chunks(chunks: Iterator[Chunk]) -> Iterator[Chunk]:
        for c in chunks:
            c.embedding = [0.1] * 768
            yield c

    embedder.embed_chunks.side_effect = side_effect_embed_chunks

    # Mock embedding for summary nodes (strings)
    # Must yield one embedding per input text.
    def side_effect_embed_strings(texts: list[str]) -> Iterator[list[float]]:
        for _ in texts:
            yield [0.2] * 768

    embedder.embed_strings.side_effect = side_effect_embed_strings

    # Clustering Logic
    # Call 1 (Level 0 Chunks): Returns 2 clusters (needs reducing)
    # Cluster 0: [0, 1], Cluster 1: [2]
    cluster_l0_0 = Cluster(id=0, level=0, node_indices=[0, 1])
    cluster_l0_1 = Cluster(id=1, level=0, node_indices=[2])

    # Call 2 (Level 1 Summaries): Returns 1 cluster (Root)
    # Cluster 0: [0, 1] (Indices into the list of summaries from L0 clusters)
    cluster_l1_0 = Cluster(id=0, level=1, node_indices=[0, 1])  # Summaries of c0 and c1

    clusterer.cluster_nodes.side_effect = [
        [cluster_l0_0, cluster_l0_1],  # First pass
        [cluster_l1_0],  # Second pass
    ]

    # Summarization
    # We must return SummaryNode, using the context passed by RaptorEngine
    summary_texts = [
        "Summary L1-0",
        "Summary L1-1",
        "Root Summary",
    ]
    summary_iter = iter(summary_texts)

    def summarize_side_effect(
        text: str | list[str], context: dict[str, Any] | None = None
    ) -> SummaryNode:
        summary_text = next(summary_iter)
        # Ensure context has ID and children
        if not context:
            context = {
                "id": str(uuid.uuid4()),
                "level": 1,
                "children_indices": [],
            }

        return SummaryNode(
            id=context["id"],
            text=summary_text,
            level=context["level"],
            children_indices=context["children_indices"],
            metadata=context.get("metadata", {}),
        )

    summarizer.summarize.side_effect = summarize_side_effect

    # Run
    # We must simulate the consumption of generator inside cluster_nodes mock side effect
    # to trigger the side effect that populates leaf_chunks.

    original_side_effect = [
        [cluster_l0_0, cluster_l0_1],  # First pass
        [cluster_l1_0],  # Second pass
    ]

    # Use closure for stateful side effect
    iter_count = 0

    def consuming_side_effect(
        embeddings: Iterator[list[float]] | list[list[float]], config: ProcessingConfig
    ) -> list[Cluster]:
        nonlocal iter_count
        # Iterate over embeddings if it's an iterator
        if isinstance(embeddings, Iterator):
            list(embeddings)

        result = original_side_effect[iter_count]
        iter_count += 1
        return result

    clusterer.cluster_nodes.side_effect = consuming_side_effect

    tree = engine.run("Long text")

    # Verify
    assert isinstance(tree, DocumentTree)
    assert tree.root_node.text == "Root Summary"
    assert tree.root_node.level == 2  # L0 -> L1 -> L2 (Root)

    # Check L1 nodes
    root_children_ids = tree.root_node.children_indices
    assert len(root_children_ids) == 2
    assert all(isinstance(uid, str) for uid in root_children_ids)

    # Verify we have all nodes
    # Root + 2 L1 nodes = 3 nodes
    assert len(tree.all_nodes) == 3
