from collections.abc import Iterable
from unittest.mock import MagicMock

import pytest

from domain_models.config import ClusteringAlgorithm, ProcessingConfig
from domain_models.manifest import Chunk
from matome.agents.summarizer import SummarizationAgent
from matome.engines.cluster import GMMClusterer
from matome.engines.embedder import EmbeddingService
from matome.engines.raptor import RaptorEngine
from matome.interfaces import Chunker
from matome.utils.store import DiskChunkStore


def test_uat_scenario_12_multi_level(tmp_path: pytest.TempPathFactory) -> None:
    """
    Scenario ID: C02-12 (Multi-Level Tree Construction)
    Objective: Verify that the pipeline creates a hierarchical tree with correct levels.
    """

    # 1. Setup Config
    # Use Enum for clustering_algorithm
    config = ProcessingConfig(
        max_tokens=100,
        chunk_buffer_size=10,
        embedding_batch_size=5,
        clustering_algorithm=ClusteringAlgorithm.GMM,
        n_clusters=2, # Force 2 clusters to ensure reduction
        random_state=42
    )

    # 2. Mock Components

    # Mock Chunker to guarantee we have enough chunks
    mock_chunker = MagicMock(spec=Chunker)
    # Generate 20 chunks to ensure we have enough for clustering
    # With n_clusters=2, we expect 2 clusters at L0 -> 2 summary nodes at L1.
    # 2 summaries might be final root?
    # If we have 2 nodes at L1, Raptor might try to cluster them.
    # If 2 nodes, n_clusters=2 might fail or produce 2 clusters of 1?
    # Raptor stops if node_count <= 1.
    # Ideally: 20 chunks -> 2 clusters (10 each) -> 2 summaries.
    # 2 summaries -> 1 cluster (2 nodes) -> 1 root.
    # Total levels: L0 (chunks), L1 (summaries), L2 (root). Root level should be 2.

    initial_chunks = [
        Chunk(index=i, text=f"Chunk {i}", start_char_idx=i*10, end_char_idx=(i+1)*10)
        for i in range(20)
    ]
    mock_chunker.split_text.return_value = iter(initial_chunks)

    # Mock Embedder
    mock_embedder = MagicMock(spec=EmbeddingService)

    # Mock Summarizer
    mock_summarizer = MagicMock(spec=SummarizationAgent)
    mock_summarizer.summarize.return_value = "Summary Text"

    # Real Clusterer (GMM)
    clusterer = GMMClusterer()

    # Store
    store_path = tmp_path / "test_chunks.db" # type: ignore[operator]
    store = DiskChunkStore(db_path=store_path)

    # Engine
    engine = RaptorEngine(mock_chunker, mock_embedder, clusterer, mock_summarizer, config)

    # 3. Execution
    text = "Dummy Text"

    # Mock behavior for embed_chunks
    def side_effect_embed_chunks(chunks: Iterable[Chunk]) -> Iterable[Chunk]:
        # Iterate and assign embeddings
        # We need to yield the same chunk objects but with embedding set
        # Since input is iterator, we consume it
        for i, chunk in enumerate(chunks):
            # Assign embedding based on index to force clusters
            # First 10 -> Cluster A, Next 10 -> Cluster B
            if i < 10:
                chunk.embedding = [1.0, 0.0]
            else:
                chunk.embedding = [0.0, 1.0]
            yield chunk

    mock_embedder.embed_chunks.side_effect = side_effect_embed_chunks

    # Mock embed_strings for summaries
    def side_effect_embed_strings(texts: Iterable[str]) -> Iterable[list[float]]:
        # For summaries, just return neutral embeddings
        # If we have 2 summaries, we want them to merge into 1 root.
        # So return same embedding for all.
        for _ in texts:
            yield [0.5, 0.5]

    mock_embedder.embed_strings.side_effect = side_effect_embed_strings

    # Run
    tree = engine.run(text, store=store)

    # 4. Assertions
    # Check tree depth
    # If chunks are L0.
    # Summaries of chunks are L1.
    # If 2 summaries are merged into 1 root, root is L2.
    assert tree.root_node.level > 1

    # Check intermediate nodes exist
    root = tree.root_node
    children_indices = root.children_indices
    assert len(children_indices) > 0

    # Check first child
    first_child_id = children_indices[0]
    assert isinstance(first_child_id, str)

    first_child = tree.all_nodes[first_child_id]
    assert first_child.level == root.level - 1
