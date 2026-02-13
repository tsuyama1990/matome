from collections.abc import Iterable
from unittest.mock import MagicMock

import pytest

from domain_models.config import ProcessingConfig
from domain_models.manifest import Chunk, DocumentTree
from matome.engines.raptor import RaptorEngine


@pytest.fixture
def mock_components() -> tuple[MagicMock, MagicMock, MagicMock, MagicMock]:
    chunker = MagicMock()
    embedder = MagicMock()
    clusterer = MagicMock()
    summarizer = MagicMock()
    return chunker, embedder, clusterer, summarizer


def test_raptor_pipeline_integration(
    mock_components: tuple[MagicMock, MagicMock, MagicMock, MagicMock],
) -> None:
    chunker, embedder, clusterer, summarizer = mock_components
    config = ProcessingConfig(embedding_batch_size=2, chunk_buffer_size=2)

    # Setup Chunker
    chunk1 = Chunk(index=0, text="chunk1", start_char_idx=0, end_char_idx=5)
    chunk2 = Chunk(index=1, text="chunk2", start_char_idx=6, end_char_idx=11)
    chunker.split_text.return_value = iter([chunk1, chunk2])

    # Setup Embedder
    # L0 embedding (chunk-based)
    chunk1.embedding = [0.1, 0.2]
    chunk2.embedding = [0.3, 0.4]

    def embed_chunks_side_effect(chunks: Iterable[Chunk]) -> Iterable[Chunk]:
        for c in chunks:
            # Simulate embedding generation
            if c.index == 0:
                c.embedding = [0.1, 0.2]
            else:
                c.embedding = [0.3, 0.4]
            yield c

    embedder.embed_chunks.side_effect = embed_chunks_side_effect

    # Setup Clusterer
    # Should receive list of lists (batches of embeddings)
    def cluster_nodes_side_effect(
        embeddings_iter: Iterable[list[list[float]]], config: ProcessingConfig
    ) -> list[MagicMock]:
        # Consume the generator to verify content
        all_embeddings = []
        for batch in embeddings_iter:
            all_embeddings.extend(batch)

        # Verify we got the correct embeddings
        assert [0.1, 0.2] in all_embeddings
        assert [0.3, 0.4] in all_embeddings

        # Return a single cluster containing all nodes
        cluster = MagicMock()
        cluster.id = 0
        cluster.node_indices = [0, 1]
        return [cluster]

    clusterer.cluster_nodes.side_effect = cluster_nodes_side_effect

    # Setup Summarizer
    summary_node = MagicMock()
    summary_node.id = "root"
    summary_node.text = "Summary"
    summary_node.level = 1
    summary_node.children_indices = [0, 1]
    # Ensure embedding is set for root
    summary_node.embedding = None
    summarizer.summarize.return_value = summary_node

    # Root embedding
    embedder.embed_strings.return_value = iter([[0.5, 0.6]])

    engine = RaptorEngine(chunker, embedder, clusterer, summarizer, config)

    # Run
    tree = engine.run("some text")

    assert isinstance(tree, DocumentTree)
    assert tree.root_node.id == "root"

    # Verify clusterer was called with embeddings
    clusterer.cluster_nodes.assert_called()
