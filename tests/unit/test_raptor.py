from collections.abc import Iterator
from unittest.mock import MagicMock, create_autospec

import pytest

from domain_models.config import ProcessingConfig
from domain_models.manifest import Chunk, Cluster, DocumentTree, SummaryNode
from domain_models.types import DIKWLevel
from matome.agents.strategies import InformationStrategy, KnowledgeStrategy, WisdomStrategy
from matome.engines.embedder import EmbeddingService
from matome.engines.raptor import RaptorEngine
from matome.exceptions import ClusteringError, MatomeError
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
    def side_effect_embed(chunks_iter: Iterator[Chunk]) -> Iterator[Chunk]:
        for c in chunks_iter:
            c.embedding = [0.1] * 768
            yield c
    embedder.embed_chunks.side_effect = side_effect_embed

    # 3. Clustering
    def cluster_side_effect(embeddings: Iterator[list[float]], config: ProcessingConfig) -> list[Cluster]:
        list(embeddings) # Consume generator to trigger store writes
        return [Cluster(id=0, level=0, node_indices=[0])]

    clusterer.cluster_nodes.side_effect = cluster_side_effect

    # Mock Summarizer
    summarizer.summarize.return_value = "Wisdom Summary"

    # Run
    tree = engine.run("Short text")

    # Verify
    embedder.embed_chunks.assert_called()
    clusterer.cluster_nodes.assert_called()
    summarizer.summarize.assert_called_once()

    assert isinstance(tree, DocumentTree)
    assert len(tree.leaf_chunk_ids) == 1
    assert tree.root_node.level == 1
    assert tree.root_node.text == "Wisdom Summary"

    # Ensure it used Wisdom strategy
    # Passed as 3rd arg (positional)
    args, kwargs = summarizer.summarize.call_args
    # args: (text, config, strategy)
    assert len(args) >= 3
    assert isinstance(args[2], WisdomStrategy)


def test_raptor_strategy_selection(
    mock_dependencies: tuple[MagicMock, ...], config: ProcessingConfig
) -> None:
    """Test that correct strategies are used for different levels."""
    chunker, embedder, clusterer, summarizer = mock_dependencies
    engine = RaptorEngine(chunker, embedder, clusterer, summarizer, config)

    # Setup: 3 Chunks -> 1 Cluster (L1 Info) -> 1 Cluster (L2 Knowledge) -> Root (L3 Wisdom)

    # Mock Chunking
    chunks = [Chunk(index=i, text=f"Chunk {i}", start_char_idx=0, end_char_idx=10) for i in range(3)]
    chunker.split_text.return_value = iter(chunks)

    # Mock embedding to return chunks with embeddings
    def side_effect_embed(chunks_iter: Iterator[Chunk]) -> Iterator[Chunk]:
        for c in chunks_iter:
            c.embedding = [0.1] * 768
            yield c
    embedder.embed_chunks.side_effect = side_effect_embed

    # Mock Clustering
    c1 = Cluster(id=0, level=0, node_indices=[0])
    c2 = Cluster(id=1, level=0, node_indices=[1, 2])

    c3 = Cluster(id=0, level=1, node_indices=[0, 1])

    # Side effect must consume generator
    cluster_results = [
        [c1, c2], # First pass (chunks -> L1)
        [c3],     # Second pass (L1 -> L2)
    ]

    # We need a mutable iterator for side effects
    result_iter = iter(cluster_results)

    def cluster_side_effect(embeddings: Iterator[list[float]], config: ProcessingConfig) -> list[Cluster]:
        list(embeddings) # Consume
        return next(result_iter)

    clusterer.cluster_nodes.side_effect = cluster_side_effect

    embedder.embed_strings.return_value = iter([[0.1]*768, [0.1]*768])

    summarizer.summarize.return_value = "Summary"

    engine.run("Text")

    # Check calls
    calls = summarizer.summarize.call_args_list
    assert len(calls) == 3

    # First 2 calls (L0 -> L1): Information
    args1, _ = calls[0]
    assert isinstance(args1[2], InformationStrategy)

    args2, _ = calls[1]
    assert isinstance(args2[2], InformationStrategy)

    # 3rd call (L1 -> L2): This creates the Root.
    # Since len(clusters) was 1 ([c3]), is_final was True.
    # So it should be WisdomStrategy.
    args3, _ = calls[2]
    assert isinstance(args3[2], WisdomStrategy)


def test_raptor_error_handling(
    mock_dependencies: tuple[MagicMock, ...], config: ProcessingConfig
) -> None:
    """Test that ClusteringError is raised/handled."""
    chunker, embedder, clusterer, summarizer = mock_dependencies
    engine = RaptorEngine(chunker, embedder, clusterer, summarizer, config)

    chunker.split_text.return_value = iter([Chunk(index=0, text="t", start_char_idx=0, end_char_idx=1)])
    # Need to return chunk with embedding
    embedder.embed_chunks.return_value = iter([Chunk(index=0, text="t", start_char_idx=0, end_char_idx=1, embedding=[0.1]*768)])

    def fail_side_effect(embeddings: Iterator[list[float]], config: ProcessingConfig) -> list[Cluster]:
        list(embeddings)
        raise Exception("Clustering failed")

    clusterer.cluster_nodes.side_effect = fail_side_effect

    with pytest.raises(MatomeError):
        engine.run("Text")
