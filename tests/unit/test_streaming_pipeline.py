import shutil
import tempfile
from collections.abc import Generator
from pathlib import Path

import pytest

from domain_models.config import ProcessingConfig
from matome.engines.chunker import JapaneseTokenChunker
from matome.engines.embedder import EmbeddingService
from matome.engines.raptor import RaptorEngine
from matome.engines.cluster import GMMClusterer
from matome.agents.summarizer import SummarizationAgent
from matome.utils.store import DiskChunkStore

@pytest.fixture
def temp_store() -> Generator[DiskChunkStore, None, None]:
    with DiskChunkStore() as store:
        yield store

@pytest.fixture
def config() -> ProcessingConfig:
    return ProcessingConfig(
        max_tokens=100,
        embedding_batch_size=2,
        chunk_buffer_size=2,
        clustering_algorithm="gmm",
        n_clusters=2,
        embedding_model="all-MiniLM-L6-v2" # small model
    )

def test_streaming_pipeline_end_to_end(config: ProcessingConfig, temp_store: DiskChunkStore) -> None:
    """
    Verifies that the entire pipeline can process text in a streaming fashion.
    This test minimizes mocking by using real components where possible (TokenChunker, RaptorEngine),
    though we still mock heavy ML parts (Embedding, Summarization) to keep it unit-test fast.
    """

    # 1. Setup Input: A list of strings simulates a file stream
    input_stream = [
        "This is sentence 1.",
        "This is sentence 2.",
        "This is sentence 3.",
        "This is sentence 4.",
    ] * 2 # 8 chunks total, enough for 2 batches

    # 2. Components
    chunker = JapaneseTokenChunker(config)

    # Mock EmbeddingService to return dummy vectors without loading model
    # We subclass to override just the heavy method
    class MockEmbedder(EmbeddingService):
        def embed_strings(self, texts):
            # Return dummy vector of dim 4
            for _ in texts:
                yield [0.1, 0.2, 0.3, 0.4]

    embedder = MockEmbedder(config)

    # Mock Summarizer
    class MockSummarizer(SummarizationAgent):
        def summarize(self, text, config=None, level=0, strategy=None) -> str:
            return f"Summary of level {level}"

    summarizer = MockSummarizer(config)

    # Mock Clusterer
    # We want to test RaptorEngine streaming, not GMM.
    # But RaptorEngine calls clusterer.cluster_nodes(generator)
    # We can use a simple clusterer implementation that consumes generator.
    from domain_models.manifest import Cluster
    class SimpleClusterer:
        def cluster_nodes(self, embeddings, config):
            # Consume embeddings
            count = sum(1 for _ in embeddings)
            # Return dummy clusters
            # If 8 items, return 2 clusters: [0..3], [4..7]
            if count == 0:
                return []
            mid = count // 2
            return [
                Cluster(id=0, level=0, node_indices=list(range(mid))),
                Cluster(id=1, level=0, node_indices=list(range(mid, count)))
            ]

    clusterer = SimpleClusterer()

    # 3. Initialize RaptorEngine
    engine = RaptorEngine(chunker, embedder, clusterer, summarizer, config)

    # 4. Run with Iterable
    tree = engine.run(input_stream, store=temp_store)

    # 5. Verify Results
    assert tree is not None
    assert tree.root_node is not None
    # We provided 8 sentences. TokenChunker (mocked tokenizer or real?)
    # Real JapaneseTokenChunker uses tiktoken. "This is sentence 1." is short.
    # 8 inputs -> 8 chunks (assuming max_tokens=100 fits one sentence).
    # SimpleClusterer splits 8 -> 2 clusters.
    # Level 1: 2 summaries.
    # Level 1 clustering: 2 items -> 1 cluster (SimpleClusterer logic needs to handle 2 items).
    # If SimpleClusterer mid = 1, it returns 2 clusters?
    # RaptorEngine loop:
    # L0 (8 nodes) -> 2 clusters.
    # L1 (2 nodes) -> clusterer called with 2 embeddings.
    # SimpleClusterer(2): mid=1 -> [0], [1]. 2 clusters.
    # RaptorEngine sees reduction failure (2 nodes -> 2 clusters).
    # It forces reduction?
    # RaptorEngine: "if len(clusters) == node_count ... Force reduction."
    # So it merges to 1 cluster.
    # L2 (1 node) -> Root.

    assert tree.root_node.level >= 1
    # Check that store has chunks
    # 8 chunks + 2 L1 summaries + 1 L2 summary = 11 nodes.
    # Or 8 chunks + 2 L1 + 1 Root = 11.

    # We can check specific counts in DB if we want, but tree.all_nodes should contain summaries.
    assert len(tree.all_nodes) >= 1
