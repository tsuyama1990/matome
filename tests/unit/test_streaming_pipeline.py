from collections.abc import Generator, Iterable, Iterator
from typing import Any

import pytest

from domain_models.config import ClusteringAlgorithm, ProcessingConfig
from matome.agents.summarizer import SummarizationAgent
from matome.engines.chunker import JapaneseTokenChunker
from matome.engines.embedder import EmbeddingService
from matome.engines.raptor import RaptorEngine
from matome.utils.store import DiskChunkStore


@pytest.fixture
def temp_store() -> Generator[DiskChunkStore, None, None]:
    with DiskChunkStore() as store:
        yield store

@pytest.fixture
def config() -> ProcessingConfig:
    # Set max_tokens low to force multiple chunks
    return ProcessingConfig(
        max_tokens=10,
        embedding_batch_size=2,
        chunk_buffer_size=2,
        clustering_algorithm=ClusteringAlgorithm.GMM,
        n_clusters=2,
        embedding_model="all-MiniLM-L6-v2",
        summarization_model="gpt-4o"
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
    ] * 2 # 8 items

    # Verify input stream is consumed lazily?
    # We can wrap it in a generator to track consumption.
    consumed_count = 0
    def input_generator() -> Iterator[str]:
        nonlocal consumed_count
        for item in input_stream:
            consumed_count += 1
            yield item

    # 2. Components
    chunker = JapaneseTokenChunker(config)

    # Mock EmbeddingService to return dummy vectors without loading model
    class MockEmbedder(EmbeddingService):
        def embed_strings(self, texts: Iterable[str]) -> Iterator[list[float]]:
            # Return dummy vector of dim 4
            for _ in texts:
                yield [0.1, 0.2, 0.3, 0.4]

    embedder = MockEmbedder(config)

    # Mock Summarizer
    class MockSummarizer(SummarizationAgent):
        def summarize(self, text: str | list[str], config: ProcessingConfig | None = None, level: int = 0, strategy: Any = None) -> str:
            return f"Summary of level {level}"

    summarizer = MockSummarizer(config)

    # Mock Clusterer
    from domain_models.manifest import Cluster
    class SimpleClusterer:
        def cluster_nodes(self, embeddings: Iterator[list[float]], config: ProcessingConfig) -> list[Cluster]:
            # Consume embeddings
            count = sum(1 for _ in embeddings)
            # Return dummy clusters
            if count == 0:
                return []
            mid = count // 2
            # Handle minimal case
            if mid == 0:
                return [Cluster(id=0, level=0, node_indices=list(range(count)))]

            return [
                Cluster(id=0, level=0, node_indices=list(range(mid))),
                Cluster(id=1, level=0, node_indices=list(range(mid, count)))
            ]

    clusterer = SimpleClusterer()

    # 3. Initialize RaptorEngine
    # Type ignore for clusterer because it doesn't fully implement protocol (missing types in signature matches but good enough for runtime)
    engine = RaptorEngine(chunker, embedder, clusterer, summarizer, config) # type: ignore[arg-type]

    # 4. Run with Iterable
    tree = engine.run(input_generator(), store=temp_store)

    # 5. Verify Results
    assert tree is not None
    assert tree.root_node is not None

    # Verify that input was fully consumed
    assert consumed_count == 8

    # Verify store content
    with temp_store.engine.connect() as conn:
        from sqlalchemy import text
        result = conn.execute(text("SELECT count(*) FROM nodes WHERE type='chunk'")).scalar()
        # Assert result is not None for mypy
        assert result is not None
        assert result > 1
