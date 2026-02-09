from collections.abc import Iterator
from unittest.mock import MagicMock

import pytest

from domain_models.config import ProcessingConfig
from domain_models.manifest import Chunk, DocumentTree
from matome.engines.cluster import GMMClusterer
from matome.engines.raptor import RaptorEngine


class DummyEmbedder:
    def __init__(self, dim: int = 384) -> None:
        self.dim = dim
        self.config = MagicMock() # Satisfy interface if needed? No, engine uses it.

    def embed_chunks(self, chunks: list[Chunk]) -> Iterator[Chunk]:
        for i, c in enumerate(chunks):
            # Create synthetic clusters
            # First half: Cluster A (1.0, 0.0...)
            # Second half: Cluster B (0.0, 1.0...)
            vec = [0.0] * self.dim
            if i < len(chunks) // 2:
                vec[0] = 1.0 + (i * 0.01)
            else:
                vec[1] = 1.0 + (i * 0.01)
            c.embedding = vec
            yield c

    def embed_strings(self, texts: list[str]) -> Iterator[list[float]]:
        for _ in texts:
            vec = [0.0] * self.dim
            vec[2] = 1.0 # Distinct from chunks
            yield vec

@pytest.fixture
def config() -> ProcessingConfig:
    return ProcessingConfig(
        umap_n_neighbors=2, # Small for test data
        umap_min_dist=0.0,
    )

def test_raptor_pipeline_integration(config: ProcessingConfig) -> None:
    """
    Test the RAPTOR pipeline with real Clusterer and mocked other components.
    Ensures that data flows correctly through the engine and clustering works.
    """
    # Components
    chunker = MagicMock()
    # Return 10 chunks to ensure enough data for clustering
    chunks = [
        Chunk(index=i, text=f"Chunk {i}", start_char_idx=0, end_char_idx=10)
        for i in range(10)
    ]
    chunker.split_text.return_value = chunks

    embedder = DummyEmbedder()

    # Real Clusterer
    # Note: GMMClusterer needs scikit-learn, umap-learn installed.
    # Assuming environment has them (uv sync verified).
    clusterer = GMMClusterer()

    summarizer = MagicMock()
    summarizer.summarize.return_value = "Summary Text"

    engine = RaptorEngine(chunker, embedder, clusterer, summarizer, config) # type: ignore
    # type ignore for DummyEmbedder not matching EmbeddingService exactly (properties vs methods)

    # Run
    tree = engine.run("Dummy text")

    # Verify
    assert isinstance(tree, DocumentTree)
    assert tree.root_node is not None
    assert len(tree.leaf_chunks) == 10

    # Verify Hierarchy
    # With 10 chunks, we expect some reduction.
    # Level 0 (Chunks) -> ... -> Root
    assert tree.root_node.level >= 1

    # Check if we have intermediate nodes
    if tree.root_node.level > 1:
        # We should have nodes in all_nodes that are not root
        assert len(tree.all_nodes) > 1
