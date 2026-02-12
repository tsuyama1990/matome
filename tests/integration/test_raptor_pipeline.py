import uuid
from collections.abc import Iterable, Iterator
from typing import Any
from unittest.mock import create_autospec

import pytest

from domain_models.config import ProcessingConfig
from domain_models.manifest import Chunk, DocumentTree, SummaryNode
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
    Uses proper mock specifications via create_autospec.
    """
    # Mock Chunker (Protocol)
    chunker = create_autospec(Chunker, instance=True)
    chunks = [
        Chunk(index=i, text=f"Chunk {i}", start_char_idx=0, end_char_idx=10) for i in range(10)
    ]
    chunker.split_text.return_value = iter(chunks)

    # Real Clusterer (Implementation)
    clusterer = GMMClusterer()

    # Mock Summarizer (Protocol)
    summarizer = create_autospec(Summarizer, instance=True)
    def summarize_side_effect(text: str | list[str], context: dict[str, Any] | None = None) -> SummaryNode:
        if context is None:
            context = {}
        return SummaryNode(
            id=context.get("id", str(uuid.uuid4())),
            text="Summary Text",
            level=context.get("level", 1),
            children_indices=context.get("children_indices", []),
            metadata=context.get("metadata", {})
        )
    summarizer.summarize.side_effect = summarize_side_effect

    # Dummy Embedder (Subclass)
    embedder = DummyEmbedder()

    # Instantiate Engine with strictly typed mocks/objects
    engine = RaptorEngine(chunker, embedder, clusterer, summarizer, config)

    # Use a store to verify persistence
    with DiskChunkStore() as store:
        tree = engine.run("Dummy text", store=store)

        assert isinstance(tree, DocumentTree)
        assert tree.root_node is not None
        assert len(tree.leaf_chunk_ids) == 10
        assert tree.root_node.level >= 1
        if tree.root_node.level > 1 and tree.all_nodes:
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

        if tree.all_nodes:
            for node in tree.all_nodes.values():
                assert node.embedding is not None, f"Summary node {node.id} must have an embedding."
