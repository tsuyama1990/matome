from collections.abc import Iterable, Iterator
from unittest.mock import create_autospec

import pytest

from domain_models.config import ProcessingConfig
from domain_models.manifest import Chunk, DocumentTree, SummaryNode
from domain_models.types import DIKWLevel
from matome.engines.cluster import GMMClusterer
from matome.engines.embedder import EmbeddingService
from matome.engines.raptor import RaptorEngine
from matome.interfaces import Chunker, Summarizer
from matome.utils.store import DiskChunkStore


class DummyEmbedder(EmbeddingService):
    def __init__(self, dim: int = 384) -> None:
        self.dim = dim
        self.config = create_autospec(ProcessingConfig)

    def embed_chunks(self, chunks: Iterable[Chunk]) -> Iterator[Chunk]:
        # Process as iterator
        for i, c in enumerate(chunks):
            vec = [0.0] * self.dim
            # Simple logic to create 2 clusters
            if i % 2 == 0:
                vec[0] = 1.0 + (i * 0.01)
            else:
                vec[1] = 1.0 + (i * 0.01)
            c.embedding = vec
            yield c

    def embed_strings(self, texts: Iterable[str]) -> Iterator[list[float]]:
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
    Verifies DIKW level assignment and memory-safe processing.
    """
    chunker = create_autospec(Chunker, instance=True)

    # Generator for chunks to simulate streaming
    def chunk_generator() -> Iterator[Chunk]:
        for i in range(10):
            yield Chunk(index=i, text=f"Chunk {i}", start_char_idx=0, end_char_idx=10)

    chunker.split_text.return_value = chunk_generator()

    clusterer = GMMClusterer()

    summarizer = create_autospec(Summarizer, instance=True)
    summarizer.summarize.return_value = "Summary Text"

    embedder = DummyEmbedder()

    engine = RaptorEngine(chunker, embedder, clusterer, summarizer, config)

    with DiskChunkStore() as store:
        tree = engine.run("Dummy text", store=store)

        assert isinstance(tree, DocumentTree)
        assert tree.root_node is not None
        root = tree.root_node
        assert isinstance(root, SummaryNode)
        assert len(tree.leaf_chunk_ids) == 10
        assert root.level >= 1

        assert root.metadata.dikw_level == DIKWLevel.WISDOM

        # Check children of root (Level 1)
        # If root is Level 2 (chunks -> L1 -> Root), then L1 should be INFORMATION (or KNOWLEDGE if depth > 2)
        # With 10 chunks and GMM, we likely get L1 nodes.
        # Let's verify at least one child exists and has correct level
        if root.children_indices:
            child_id = root.children_indices[0]
            child_node = store.get_node(child_id)
            if child_node and isinstance(child_node, SummaryNode):
                # If level is 1 (directly above chunks), it should be INFORMATION
                if child_node.level == 1:
                    assert child_node.metadata.dikw_level == DIKWLevel.INFORMATION
                # If intermediate level
                elif child_node.level > 1:
                    assert child_node.metadata.dikw_level == DIKWLevel.KNOWLEDGE

        first_chunk = store.get_node(tree.leaf_chunk_ids[0])
        assert first_chunk is not None
        assert first_chunk.embedding is not None, "Leaf chunks must retain embeddings."

        root_fetched = store.get_node(root.id)
        if root_fetched:
            assert root_fetched.embedding is not None, "Root node must have an embedding in store."

        assert root.embedding is not None, "Root node object must have an embedding."
