from collections.abc import Iterator
from unittest.mock import MagicMock

import pytest

from domain_models.config import ProcessingConfig
from domain_models.manifest import Chunk
from matome.engines.cluster import GMMClusterer
from matome.engines.raptor import RaptorEngine


class UATEmbedder:
    def __init__(self, dim: int = 384) -> None:
        self.dim = dim
        self.config = MagicMock()

    def embed_chunks(self, chunks: list[Chunk]) -> Iterator[Chunk]:
        # Create clear clusters based on index
        # This ensures that GMMClusterer finds structure
        for c in chunks:
            vec = [0.0] * self.dim
            # Cluster 0: indices 0-9
            # Cluster 1: indices 10-19
            # ...
            # We map chunk index to a dimension in vector space to make them orthogonal
            # But dim is limited.
            # Let's use simple logic:
            # 5 groups of 10 chunks.
            group_id = c.index // 10
            # Set a unique dimension for each group
            if group_id < self.dim:
                vec[group_id] = 1.0
            c.embedding = vec
            yield c

    def embed_strings(self, texts: list[str]) -> Iterator[list[float]]:
        for _ in texts:
            # Summary embeddings
            # Make them distinct so they might cluster again or merge
            vec = [0.0] * self.dim
            # Put them in a different subspace?
            # Or make them all similar to force merge?
            # If we want depth 2, summaries must merge into 1 root.
            vec[100] = 1.0
            yield vec

@pytest.fixture
def uat_config() -> ProcessingConfig:
    return ProcessingConfig(
        umap_n_neighbors=5, # Slightly larger for 50 chunks
        umap_min_dist=0.0,
    )

def test_uat_scenario_11_single_level(uat_config: ProcessingConfig) -> None:
    """
    Scenario 11: Single-Level Summarization (Priority: Medium)
    Goal: Ensure the system handles short documents correctly (no recursion needed).
    Expected Outcome: The RAPTOR engine returns a tree with Depth 1 (Root -> Chunks).
    """
    chunker = MagicMock()
    # 3 chunks (small enough to be one cluster)
    chunks = [
        Chunk(index=i, text=f"Chunk {i}", start_char_idx=0, end_char_idx=10)
        for i in range(3)
    ]
    chunker.split_text.return_value = chunks

    embedder = UATEmbedder()

    # GMMClusterer handles small input < 3 by returning 1 cluster.
    clusterer = GMMClusterer()

    summarizer = MagicMock()
    summarizer.summarize.return_value = "Summary Root"

    engine = RaptorEngine(chunker, embedder, clusterer, summarizer, uat_config) # type: ignore
    tree = engine.run("Short doc")

    # 3 chunks -> 1 cluster -> 1 Summary (Root)
    # Level 1.
    assert tree.root_node.level == 1
    assert len(tree.leaf_chunks) == 3
    assert tree.root_node.text == "Summary Root"

def test_uat_scenario_12_multi_level(uat_config: ProcessingConfig) -> None:
    """
    Scenario 12: Multi-Level Tree Construction (Priority: High)
    Goal: Ensure the recursive logic builds a hierarchy for long documents.
    Expected Outcome: The RAPTOR engine returns a tree with Depth >= 2.
    """
    chunker = MagicMock()
    # 50 chunks
    # UATEmbedder will create 5 clusters (indices 0-9, 10-19, etc.)
    chunks = [
        Chunk(index=i, text=f"Chunk {i}", start_char_idx=0, end_char_idx=10)
        for i in range(50)
    ]
    chunker.split_text.return_value = chunks

    embedder = UATEmbedder()

    # GMMClusterer should find clusters in 50 orthogonal items?
    # Actually, UMAP might reduce them to 2D.
    # If they are orthogonal in high dim, UMAP projects them.
    # They should form distinct blobs.
    clusterer = GMMClusterer()

    summarizer = MagicMock()
    summarizer.summarize.return_value = "Summary Node"

    engine = RaptorEngine(chunker, embedder, clusterer, summarizer, uat_config) # type: ignore
    tree = engine.run("Long doc")

    # 50 chunks -> Multiple clusters -> Multiple Summaries (L1).
    # Multiple Summaries -> ... -> Root (L2+).
    assert tree.root_node.level >= 2
    assert len(tree.leaf_chunks) == 50
    # Check that we have intermediate summaries
    assert len(tree.all_nodes) > 1

def test_uat_scenario_13_summary_coherence() -> None:
    """
    Scenario 13: Summary Coherence Check (Priority: High)
    Goal: Ensure the generated summary captures the main idea.
    Note: Since we mock LLM, we verify that the summarizer is called with expected text.
    """
    config = ProcessingConfig(umap_n_neighbors=2, umap_min_dist=0.0)

    chunker = MagicMock()
    chunks = [
        Chunk(index=0, text="Climate change is real.", start_char_idx=0, end_char_idx=20),
        Chunk(index=1, text="Sea levels are rising.", start_char_idx=20, end_char_idx=40)
    ]
    chunker.split_text.return_value = chunks

    embedder = UATEmbedder()
    clusterer = GMMClusterer()

    summarizer = MagicMock()
    summarizer.summarize.return_value = "Global Warming Summary"

    engine = RaptorEngine(chunker, embedder, clusterer, summarizer, config) # type: ignore
    tree = engine.run("Climate doc")

    # Verify coherence (mocked)
    assert tree.root_node.text == "Global Warming Summary"

    # Verify summarizer was called with combined text
    # The call argument should contain chunk texts
    calls = summarizer.summarize.call_args_list
    assert len(calls) > 0
    # Check content of first call
    args, _ = calls[0]
    input_text = args[0]
    assert "Climate change is real." in input_text
    assert "Sea levels are rising." in input_text
