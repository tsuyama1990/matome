from collections.abc import Iterator
from unittest.mock import MagicMock

import pytest

from domain_models.config import ProcessingConfig
from domain_models.manifest import Chunk, DocumentTree
from matome.engines.cluster import GMMClusterer
from matome.engines.raptor import RaptorEngine
from matome.interfaces import Chunker, Summarizer
from matome.utils.store import DiskChunkStore


class DummyEmbedder:
    def __init__(self, dim: int = 384) -> None:
        self.dim = dim
        self.config = MagicMock()

    def embed_chunks(self, chunks: Iterator[Chunk]) -> Iterator[Chunk]:
        # Consume iterator
        chunk_list = list(chunks)
        for i, c in enumerate(chunk_list):
            vec = [0.0] * self.dim
            if i < len(chunk_list) // 2:
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
    chunker.split_text.return_value = iter(chunks)

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

    # Use a store to verify persistence
    with DiskChunkStore() as store:
        tree = engine.run("Dummy text", store=store)

        assert isinstance(tree, DocumentTree)
        assert tree.root_node is not None
        assert len(tree.leaf_chunk_ids) == 10
        assert tree.root_node.level >= 1
        if tree.root_node.level > 1:
            assert len(tree.all_nodes) > 1

        # Verify embeddings are present in store
        first_chunk = store.get_node(tree.leaf_chunk_ids[0])
        assert first_chunk is not None
        assert first_chunk.embedding is not None, "Leaf chunks must retain embeddings."

        # Verify root embedding
        # Root might be in store (SummaryNode) or if level 0, it's chunk.
        # But get_node works for both.
        root_fetched = store.get_node(tree.root_node.id)
        if root_fetched:
            assert root_fetched.embedding is not None, "Root node must have an embedding in store."

        assert tree.root_node.embedding is not None, "Root node object must have an embedding."

        for node in tree.all_nodes.values():
            assert node.embedding is not None, f"Summary node {node.id} must have an embedding."
