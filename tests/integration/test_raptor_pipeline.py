from collections.abc import Iterator
from unittest.mock import MagicMock

import pytest

from domain_models.config import ProcessingConfig
from domain_models.manifest import Chunk, DocumentTree
from matome.engines.cluster import GMMClusterer
from matome.engines.raptor import RaptorEngine
from matome.interfaces import Chunker, Summarizer


class DummyEmbedder:
    def __init__(self, dim: int = 384) -> None:
        self.dim = dim
        self.config = MagicMock()

    def embed_chunks(self, chunks: list[Chunk]) -> Iterator[Chunk]:
        for i, c in enumerate(chunks):
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
            vec[2] = 1.0
            yield vec


@pytest.fixture
def config() -> ProcessingConfig:
    return ProcessingConfig(
        umap_n_neighbors=2,
        umap_min_dist=0.0,
    )


def test_raptor_pipeline_integration(config: ProcessingConfig) -> None:
    """
    Test the RAPTOR pipeline with real Clusterer and mocked other components.
    Uses proper mock specifications.
    """
    # Create mocks that adhere to specs if possible, but here we use MagicMock
    # as strict typing is checked in unit tests.

    # Mock Chunker (Protocol)
    chunker = MagicMock(spec=Chunker)
    chunks = [
        Chunk(index=i, text=f"Chunk {i}", start_char_idx=0, end_char_idx=10) for i in range(10)
    ]
    chunker.split_text.return_value = chunks

    # Real Clusterer (Implementation)
    clusterer = GMMClusterer()

    # Mock Summarizer (Protocol)
    summarizer = MagicMock(spec=Summarizer)
    summarizer.summarize.return_value = "Summary Text"

    # Dummy Embedder (Helper Class)
    embedder = DummyEmbedder()

    # Instantiate Engine with strictly typed mocks/objects
    # We cast embedder because it's a dummy class satisfying implicit interface used by Raptor
    engine = RaptorEngine(chunker, embedder, clusterer, summarizer, config)  # type: ignore

    tree = engine.run("Dummy text")

    assert isinstance(tree, DocumentTree)
    assert tree.root_node is not None
    assert len(tree.leaf_chunks) == 10
    assert tree.root_node.level >= 1
    if tree.root_node.level > 1:
        assert len(tree.all_nodes) > 1
