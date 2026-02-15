from unittest.mock import MagicMock

from domain_models.config import ProcessingConfig
from matome.agents.summarizer import SummarizationAgent
from matome.engines.cluster import GMMClusterer
from matome.engines.embedder import EmbeddingService
from matome.engines.raptor import RaptorEngine
from matome.engines.token_chunker import JapaneseTokenChunker


def test_full_pipeline_flow() -> None:
    """
    End-to-End verification of the data flow:
    Text -> Chunker -> EmbeddingService -> Clusterer -> Summarizer
    """
    # Arrange
    text = (
        "これはテストです。文書を分割し、クラスタリングし、要約します。" * 5
    )  # Make it long enough for multiple chunks
    # Fix: Ensure max_summary_tokens <= max_tokens
    config = ProcessingConfig(
        max_tokens=20,  # Small token limit to force multiple chunks
        max_summary_tokens=10,
        umap_n_neighbors=2,  # Small neighbors for small dataset
        umap_min_dist=0.0,  # Default
        write_batch_size=5,  # Small batch size for testing streaming
    )

    # Use real lightweight components where possible, mocks for heavy ones
    chunker = JapaneseTokenChunker()

    # Mock Embedder
    embedder = MagicMock(spec=EmbeddingService)
    # Return dummy embeddings (dim=2 for simple clustering)
    # We need to mock embed_chunks to return chunks with embeddings
    def mock_embed_chunks(chunks_iter):
        for chunk in chunks_iter:
            chunk.embedding = [0.1, 0.2]
            yield chunk
    embedder.embed_chunks.side_effect = mock_embed_chunks
    embedder.embed_strings.return_value = iter([[0.1, 0.2]])

    # Real Clusterer (GMM is fast enough for small data)
    # However, GMM might fail with very few points if not configured carefully.
    # We'll use a mock clusterer to ensure flow stability and avoid sklearn complexity in unit test.
    clusterer = MagicMock()
    from domain_models.manifest import Cluster
    # Mock clustering result: 1 cluster containing all chunks
    # IMPORTANT: Clusterer side effect must consume the input generator!
    def mock_cluster_nodes(embeddings_iter, config):
        _ = list(embeddings_iter) # Consume
        # Assume we have chunks 0, 1, ...
        # Return 1 cluster.
        return [Cluster(id=0, level=0, node_indices=[0, 1])]

    clusterer.cluster_nodes.side_effect = mock_cluster_nodes

    # Mock Summarizer
    summarizer = MagicMock(spec=SummarizationAgent)
    summarizer.summarize.return_value = "Summary text."

    engine = RaptorEngine(chunker, embedder, clusterer, summarizer, config)

    # Act
    tree = engine.run(text)

    # Assert
    assert tree is not None
    assert tree.root_node.text == "Summary text."

    # Verify interactions
    embedder.embed_chunks.assert_called()
    clusterer.cluster_nodes.assert_called()
    summarizer.summarize.assert_called()
