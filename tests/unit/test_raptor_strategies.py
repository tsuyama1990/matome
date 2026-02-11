from unittest.mock import MagicMock, create_autospec

import pytest

from domain_models.config import ProcessingConfig
from domain_models.manifest import Chunk, Cluster
from domain_models.types import DIKWLevel
from matome.agents.strategies import ActionStrategy, KnowledgeStrategy, WisdomStrategy
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


def test_raptor_strategies_and_levels(
    mock_dependencies: tuple[MagicMock, ...], config: ProcessingConfig
) -> None:
    chunker, embedder, clusterer, summarizer = mock_dependencies
    engine = RaptorEngine(chunker, embedder, clusterer, summarizer, config)

    # Setup 3 chunks
    chunks = [
        Chunk(
            index=i, text=f"Chunk {i}", start_char_idx=i, end_char_idx=i + 1, embedding=[0.1]
        )
        for i in range(3)
    ]
    chunker.split_text.return_value = iter(chunks)
    embedder.embed_chunks.return_value = iter(chunks)

    # Clustering:
    # Pass 1 (L0->L1): 2 clusters.
    # Pass 2 (L1->L2): 1 cluster.
    # Pass 3 (L2->L3): 1 cluster (Root).

    # To test WisdomStrategy (L3+), we need depth 3.
    # L0: [0,1,2,3] -> L1: [A(0,1), B(2,3)] -> L2: [C(A,B)] -> Wait, if L2 is root, it's Knowledge.
    # We need L3 as root to test Wisdom.
    # L0: 8 chunks.
    # L0->L1: 4 clusters.
    # L1->L2: 2 clusters.
    # L2->L3: 1 cluster.

    # Simpler: Just mock side_effect to control loop count.
    # We don't strictly need real chunk count logic if we mock clusterer results.
    # But RaptorEngine checks indices bounds!
    # So we need consistent indices.

    # Let's verify Action (L1) and Knowledge (L2) first.
    # L0: 3 chunks.
    # L0 -> L1: 2 clusters.
    # L1 -> L2: 1 cluster (Root).

    cluster_l0_0 = Cluster(id=0, level=0, node_indices=[0, 1])
    cluster_l0_1 = Cluster(id=1, level=0, node_indices=[2])
    cluster_l1_0 = Cluster(id=0, level=1, node_indices=[0, 1])

    # Mock clusterer side effect
    call_count = 0
    def cluster_side_effect(embeddings, config):
        nonlocal call_count
        call_count += 1
        _ = list(embeddings) # consume
        if call_count == 1:
            return [cluster_l0_0, cluster_l0_1]
        if call_count == 2:
            return [cluster_l1_0]
        return []

    clusterer.cluster_nodes.side_effect = cluster_side_effect

    # Mock summarizer
    summarizer.summarize.return_value = "Summary"

    # Mock embed_strings for summaries (needs to yield for each summary generated)
    # L1 generates 2 summaries. L2 generates 1 summary. Total 3 calls to embed_strings (batched).
    # embed_strings is called in _process_embedding_batch.
    embedder.embed_strings.side_effect = lambda texts: iter([[0.2]] * len(texts))

    engine.run("text")

    # Expect 3 summarizer calls
    # Call 1 & 2: Level 1 (ActionStrategy)
    # Call 3: Level 2 (KnowledgeStrategy)

    assert summarizer.summarize.call_count == 3
    calls = summarizer.summarize.call_args_list

    # Level 1 calls
    args1, kwargs1 = calls[0]
    assert kwargs1['level'] == 1
    assert isinstance(kwargs1['strategy'], ActionStrategy)

    args2, kwargs2 = calls[1]
    assert kwargs2['level'] == 1
    assert isinstance(kwargs2['strategy'], ActionStrategy)

    # Level 2 call
    args3, kwargs3 = calls[2]
    assert kwargs3['level'] == 2
    assert isinstance(kwargs3['strategy'], KnowledgeStrategy)
