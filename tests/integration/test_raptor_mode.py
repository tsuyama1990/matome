from collections.abc import Iterable, Iterator
from unittest.mock import MagicMock

import pytest

from domain_models.config import ProcessingConfig, ProcessingMode
from domain_models.manifest import Chunk, Cluster, SummaryNode
from domain_models.types import DIKWLevel, NodeID
from matome.engines.embedder import EmbeddingService
from matome.engines.raptor import RaptorEngine
from matome.interfaces import Chunker, Clusterer, Summarizer
from matome.utils.store import DiskChunkStore


class MockEmbedder(EmbeddingService):
    def __init__(self) -> None:
        pass

    def embed_chunks(self, chunks: Iterable[Chunk]) -> Iterator[Chunk]:
        for c in chunks:
            c.embedding = [0.1] * 10
            yield c

    def embed_strings(self, texts: Iterable[str]) -> Iterator[list[float]]:
        for _ in texts:
            yield [0.1] * 10


class MockClusterer(Clusterer):
    """
    Deterministically clusters nodes into pairs.
    """
    def cluster_nodes(
        self, embeddings: Iterable[list[float]], config: ProcessingConfig
    ) -> list[Cluster]:
        # Consume embeddings to know count
        emb_list = list(embeddings)
        count = len(emb_list)
        clusters = []
        for cluster_id, i in enumerate(range(0, count, 2)):
            indices: list[NodeID] = [i, i + 1] if i + 1 < count else [i]
            clusters.append(Cluster(id=cluster_id, level=0, node_indices=indices))
        return clusters


class MockChunker(Chunker):
    def split_text(
        self, text: str | Iterable[str], config: ProcessingConfig
    ) -> Iterable[Chunk]:
        # Return 8 chunks to ensure 3 levels of summarization (8 -> 4 -> 2 -> 1)
        for i in range(8):
            yield Chunk(
                index=i,
                text=f"Chunk {i}",
                start_char_idx=i*10,
                end_char_idx=(i+1)*10,
                embedding=[0.1]*10
            )


@pytest.fixture
def mock_components() -> tuple[MockChunker, MockEmbedder, MockClusterer, MagicMock]:
    return MockChunker(), MockEmbedder(), MockClusterer(), MagicMock(spec=Summarizer)


def test_raptor_dikw_mode(
    mock_components: tuple[MockChunker, MockEmbedder, MockClusterer, MagicMock],
) -> None:
    chunker, embedder, clusterer, summarizer = mock_components
    summarizer.summarize.return_value = "Summary"

    config = ProcessingConfig(
        processing_mode=ProcessingMode.DIKW,
        chunk_buffer_size=10,
        embedding_batch_size=10,
        max_input_length=10000
    )

    engine = RaptorEngine(chunker, embedder, clusterer, summarizer, config)

    with DiskChunkStore() as store:
        tree = engine.run("dummy text", store=store)

        # Verify Levels
        # L0: 8 chunks
        # L1: 4 summaries
        # L2: 2 summaries
        # L3: 1 summary (Root)

        assert tree.root_node.level == 3

        # Check DIKW levels
        l3_node = tree.root_node
        assert l3_node.metadata.dikw_level == DIKWLevel.WISDOM

        l2_nodes = [store.get_node(idx) for idx in l3_node.children_indices]
        for node in l2_nodes:
            assert isinstance(node, SummaryNode)
            assert node.metadata.dikw_level == DIKWLevel.KNOWLEDGE

            l1_nodes = [store.get_node(idx) for idx in node.children_indices]
            for l1_node in l1_nodes:
                assert isinstance(l1_node, SummaryNode)
                assert l1_node.metadata.dikw_level == DIKWLevel.INFORMATION


def test_raptor_default_mode(
    mock_components: tuple[MockChunker, MockEmbedder, MockClusterer, MagicMock],
) -> None:
    chunker, embedder, clusterer, summarizer = mock_components
    summarizer.summarize.return_value = "Summary"

    config = ProcessingConfig(
        processing_mode=ProcessingMode.DEFAULT,
        chunk_buffer_size=10,
        embedding_batch_size=10,
        max_input_length=10000
    )

    engine = RaptorEngine(chunker, embedder, clusterer, summarizer, config)

    with DiskChunkStore() as store:
        tree = engine.run("dummy text", store=store)

        assert tree.root_node.level == 3

        # Check DIKW levels - Should be INFORMATION for all summaries in DEFAULT mode
        # (based on my implementation choice)
        l3_node = tree.root_node
        assert l3_node.metadata.dikw_level == DIKWLevel.INFORMATION

        l2_nodes = [store.get_node(idx) for idx in l3_node.children_indices]
        for node in l2_nodes:
            assert isinstance(node, SummaryNode)
            assert node.metadata.dikw_level == DIKWLevel.INFORMATION

            l1_nodes = [store.get_node(idx) for idx in node.children_indices]
            for l1_node in l1_nodes:
                assert isinstance(l1_node, SummaryNode)
                assert l1_node.metadata.dikw_level == DIKWLevel.INFORMATION
