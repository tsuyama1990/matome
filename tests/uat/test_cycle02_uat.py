from collections.abc import Iterator
from typing import Any
from unittest.mock import MagicMock, create_autospec

import pytest

from domain_models.config import ProcessingConfig, ProcessingMode
from domain_models.manifest import Chunk, Cluster
from domain_models.types import DIKWLevel
from matome.agents.strategies import ActionStrategy, KnowledgeStrategy, WisdomStrategy
from matome.engines.embedder import EmbeddingService
from matome.engines.raptor import RaptorEngine
from matome.interfaces import Chunker, Clusterer, PromptStrategy, Summarizer


@pytest.fixture
def mock_dependencies() -> tuple[MagicMock, MagicMock, MagicMock, MagicMock]:
    chunker = create_autospec(Chunker, instance=True)
    embedder = create_autospec(EmbeddingService, instance=True)
    clusterer = create_autospec(Clusterer, instance=True)
    summarizer = create_autospec(Summarizer, instance=True)
    return chunker, embedder, clusterer, summarizer


@pytest.fixture
def config() -> ProcessingConfig:
    return ProcessingConfig(processing_mode=ProcessingMode.DIKW)


def make_cluster_side_effect(return_values_list: list[list[Cluster]]) -> Any:
    iterator = iter(return_values_list)
    def side_effect(embeddings: Any, config: ProcessingConfig) -> list[Cluster]:
        if isinstance(embeddings, Iterator):
            list(embeddings) # consume
        try:
            return next(iterator)
        except StopIteration:
            return []
    return side_effect


def test_uat_full_dikw_hierarchy(
    mock_dependencies: tuple[MagicMock, ...], config: ProcessingConfig
) -> None:
    """
    Combined UAT Scenario for Cycle 02.
    Verifies Wisdom (L3), Knowledge (L2), and Action (L1) strategies.

    Simulation Plan:
    - Start with 8 Chunks (Level 0).
    - Pass 1 (L0 -> L1): Cluster 8 chunks into 4 clusters. Produces 4 Action summaries.
    - Pass 2 (L1 -> L2): Cluster 4 summaries into 2 clusters. Produces 2 Knowledge summaries.
    - Pass 3 (L2 -> L3): Cluster 2 summaries into 1 cluster. Produces 1 Wisdom summary.
    - Pass 4 (L3 -> Stop): 1 node remaining. Stop.
    """
    chunker, embedder, clusterer, summarizer = mock_dependencies
    engine = RaptorEngine(chunker, embedder, clusterer, summarizer, config)

    # 1. Mock Chunker (8 chunks)
    chunks = [
        Chunk(index=i, text=f"chunk_{i}", start_char_idx=i, end_char_idx=i+1, embedding=[0.1]*768)
        for i in range(8)
    ]
    chunker.split_text.return_value = iter(chunks)

    # 2. Mock Embedder (Chunks)
    embedder.embed_chunks.return_value = iter(chunks)

    # 3. Mock Embedder (Strings - for summaries)
    # We will just return dummy embeddings for any list of strings
    embedder.embed_strings.side_effect = lambda texts: iter([[0.1]*768] * len(texts))

    # 4. Mock Clusters
    # Pass 1: 8 nodes -> 4 clusters ([0,1], [2,3], [4,5], [6,7])
    clusters_p1 = [
        Cluster(id=f"p1_c{i}", level=0, node_indices=[i*2, i*2+1])
        for i in range(4)
    ]

    # Pass 2: 4 nodes -> 2 clusters ([0,1], [2,3])
    clusters_p2 = [
        Cluster(id=f"p2_c{i}", level=1, node_indices=[i*2, i*2+1])
        for i in range(2)
    ]

    # Pass 3: 2 nodes -> 1 cluster ([0,1])
    clusters_p3 = [
        Cluster(id="p3_c0", level=2, node_indices=[0, 1])
    ]

    clusterer.cluster_nodes.side_effect = make_cluster_side_effect([
        clusters_p1,
        clusters_p2,
        clusters_p3,
        [] # Pass 4 (L3 input, should not happen or return empty if called)
    ])

    # 5. Mock Summarizer to capture strategies
    captured_strategies: dict[int, list[PromptStrategy | None]] = {
        1: [],
        2: [],
        3: []
    }

    def summarize_side_effect(text: str | list[str], config: ProcessingConfig, level: int = 0, strategy: PromptStrategy | None = None) -> str:
        if level in captured_strategies:
            captured_strategies[level].append(strategy)
        return f"Summary Level {level}"

    summarizer.summarize.side_effect = summarize_side_effect

    # Run
    tree = engine.run("input text")

    # --- VERIFICATION ---

    # Scenario 2.1: Wisdom Check (Root Level / L3)
    assert len(captured_strategies[3]) == 1
    assert isinstance(captured_strategies[3][0], WisdomStrategy)

    # Scenario 2.2: Action Check (Leaf/Twig Level / L1)
    assert len(captured_strategies[1]) == 4
    for strategy in captured_strategies[1]:
        assert isinstance(strategy, ActionStrategy)

    # Scenario 2.3: Knowledge Check (L2) and Hierarchy
    assert len(captured_strategies[2]) == 2
    for strategy in captured_strategies[2]:
        assert isinstance(strategy, KnowledgeStrategy)

    # Verify Tree Root
    # The root should be the single summary from L3
    assert tree.root_node.level == 3
    assert tree.root_node.metadata.dikw_level == DIKWLevel.WISDOM
    assert tree.root_node.text == "Summary Level 3"

    # Verify Metadata in tree
    # Check a random L1 node
    # Since we don't have easy access to IDs without traversing, we iterate all_nodes
    l1_nodes = [n for n in tree.all_nodes.values() if n.level == 1]
    assert len(l1_nodes) == 4
    for n in l1_nodes:
        assert n.metadata.dikw_level == DIKWLevel.INFORMATION

    l2_nodes = [n for n in tree.all_nodes.values() if n.level == 2]
    assert len(l2_nodes) == 2
    for n in l2_nodes:
        assert n.metadata.dikw_level == DIKWLevel.KNOWLEDGE
