from collections.abc import Iterator
from unittest.mock import MagicMock, create_autospec

import pytest

from domain_models.config import ProcessingConfig
from domain_models.manifest import Chunk, Cluster, DocumentTree
from domain_models.types import NodeID
from matome.agents.strategies import InformationStrategy, WisdomStrategy
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
            # Use config value if possible or standard size
            c.embedding = [0.1] * 768
            yield c
    embedder.embed_chunks.side_effect = side_effect_embed

    # 3. Clustering
    def cluster_side_effect(embeddings: Iterator[list[float]], config: ProcessingConfig) -> list[Cluster]:
        for _ in embeddings:
            pass  # Consume generator to trigger store writes without storing
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
    args, kwargs = summarizer.summarize.call_args
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
        for _ in embeddings:
            pass  # Consume without storing
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
        for _ in embeddings:
            pass  # Consume without storing
        msg = "Clustering failed"
        raise ClusteringError(msg)  # Use specific exception type

    clusterer.cluster_nodes.side_effect = fail_side_effect

    with pytest.raises(MatomeError):
        engine.run("Text")

def test_raptor_input_validation(
    mock_dependencies: tuple[MagicMock, ...], config: ProcessingConfig
) -> None:
    """Test validation logic."""
    chunker, embedder, clusterer, summarizer = mock_dependencies
    engine = RaptorEngine(chunker, embedder, clusterer, summarizer, config)

    with pytest.raises(ValueError, match="Input text must be a non-empty string"):
        engine.run("")

    large_text = "a" * (config.max_input_length + 100)
    with pytest.raises(ValueError, match="Input text length"):
        engine.run(large_text)


def test_raptor_cluster_edge_cases(
    mock_dependencies: tuple[MagicMock, ...], config: ProcessingConfig
) -> None:
    """Test empty clusters and invalid indices handling."""
    chunker, embedder, clusterer, summarizer = mock_dependencies
    engine = RaptorEngine(chunker, embedder, clusterer, summarizer, config)

    # Mock store behavior
    store = MagicMock()
    store.get_node.return_value = Chunk(index=0, text="valid", start_char_idx=0, end_char_idx=5)

    # Setup inputs for _summarize_clusters
    current_level_ids: list[NodeID] = [0, 1, 2] # 3 nodes available

    # 1. Cluster with invalid index (out of bounds) -> Should be skipped
    c1 = Cluster(id=0, level=0, node_indices=[99])

    # 2. Cluster with valid index but node missing in store -> Should be skipped
    c2 = Cluster(id=1, level=0, node_indices=[1])

    # 3. Valid cluster
    c3 = Cluster(id=2, level=0, node_indices=[0])

    clusters = [c1, c2, c3]
    strategy = InformationStrategy()

    # Mock store to return None for index 1 (missing node)
    def get_node_side_effect(nid: int | str) -> Chunk | None:
        if nid == 1:
            return None
        return Chunk(index=int(nid), text=f"text_{nid}", start_char_idx=0, end_char_idx=5)

    store.get_node.side_effect = get_node_side_effect

    # Mock summarizer return value
    summarizer.summarize.return_value = "Mock Summary"

    # Run private method directly to verify generator logic
    results = list(engine._summarize_clusters(clusters, current_level_ids, store, 1, strategy))

    # Only c3 should produce a result
    assert len(results) == 1
    assert results[0].metadata.cluster_id == 2
    assert results[0].children_indices == [0]


def test_raptor_cluster_truncation(
    mock_dependencies: tuple[MagicMock, ...], config: ProcessingConfig
) -> None:
    """Test that cluster texts are truncated if they exceed limits."""
    chunker, embedder, clusterer, summarizer = mock_dependencies

    # Set a valid limit for testing (must be >= 100)
    config_small = ProcessingConfig(max_input_length=100)
    engine = RaptorEngine(chunker, embedder, clusterer, summarizer, config_small)

    store = MagicMock()
    # 3 chunks, each 60 chars. Total 180 > 100.
    t1 = "A" * 60
    t2 = "B" * 60
    t3 = "C" * 60

    c1 = Chunk(index=1, text=t1, start_char_idx=0, end_char_idx=60)
    c2 = Chunk(index=2, text=t2, start_char_idx=60, end_char_idx=120)
    c3 = Chunk(index=3, text=t3, start_char_idx=120, end_char_idx=180)

    def get_node_side_effect(nid: int | str) -> Chunk | None:
        return {1: c1, 2: c2, 3: c3}.get(nid)  # type: ignore

    store.get_node.side_effect = get_node_side_effect

    current_level_ids: list[NodeID] = [1, 2, 3]
    cluster = Cluster(id=0, level=0, node_indices=[0, 1, 2]) # Points to ids 1, 2, 3
    strategy = InformationStrategy()

    summarizer.summarize.return_value = "Summary"

    results = list(engine._summarize_clusters([cluster], current_level_ids, store, 1, strategy))

    assert len(results) == 1

    # summarizer should be called with truncated text
    args, _ = summarizer.summarize.call_args
    passed_text = args[0]

    # 60 + 60 = 120. Loop 1 (60) OK. Loop 2 (120) Break.
    # So passed text should contain only t1 (or t1+t2 depending on exact logic).
    # Logic: if current_length + text_len > max: break.
    # 0 + 60 <= 100 OK. current=60.
    # 60 + 60 > 100 Break.
    # Only t1 included.

    assert t1 in passed_text
    assert t2 not in passed_text
    assert t3 not in passed_text

    assert len(passed_text) <= 100
