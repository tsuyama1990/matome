
from collections.abc import Generator, Iterable, Iterator
from unittest.mock import MagicMock

import pytest

from domain_models.config import ClusteringAlgorithm, ProcessingConfig
from domain_models.manifest import Chunk, Cluster
from matome.engines.embedder import EmbeddingService
from matome.engines.raptor import RaptorEngine
from matome.interfaces import Chunker, Clusterer, Summarizer
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
    Reduced complexity.
    """
    input_list = ["This is sentence 1.", "This is sentence 2.", "This is sentence 3.", "This is sentence 4."] * 2

    def input_generator() -> Iterator[str]:
        yield from input_list

    # Components
    chunker = _create_mock_chunker()
    embedder = _create_mock_embedder()
    summarizer = MagicMock(spec=Summarizer)
    summarizer.summarize.return_value = "Summary text"
    clusterer = _create_mock_clusterer()

    engine = RaptorEngine(chunker, embedder, clusterer, summarizer, config)
    engine.run(input_generator(), store=temp_store)

    # Assertions
    assert chunker.split_text.called
    assert embedder.embed_chunks.called
    assert clusterer.cluster_nodes.called
    assert summarizer.summarize.called

def _create_mock_chunker() -> MagicMock:
    chunker = MagicMock(spec=Chunker)
    def split_text_side_effect(text: str | Iterable[str], config: ProcessingConfig) -> Iterator[Chunk]:
        if not isinstance(text, (Iterator, Iterable)):
             pytest.fail("Chunker did not receive an iterable/iterator!")
        for i, t in enumerate(text):
            yield Chunk(index=i, text=t, start_char_idx=0, end_char_idx=len(t))
    chunker.split_text.side_effect = split_text_side_effect
    return chunker

def _create_mock_embedder() -> MagicMock:
    embedder = MagicMock(spec=EmbeddingService)
    def embed_chunks_side_effect(chunks: Iterable[Chunk]) -> Iterator[Chunk]:
        if not isinstance(chunks, (Iterator, Iterable)):
             pytest.fail("Embedder.embed_chunks did not receive an iterator!")
        for chunk in chunks:
            chunk.embedding = [0.1] * 4
            yield chunk
    embedder.embed_chunks.side_effect = embed_chunks_side_effect

    def embed_strings_side_effect(texts: Iterable[str]) -> Iterator[list[float]]:
        for _ in texts:
            yield [0.1] * 4
    embedder.embed_strings.side_effect = embed_strings_side_effect
    return embedder

def _create_mock_clusterer() -> MagicMock:
    clusterer = MagicMock(spec=Clusterer)
    def cluster_nodes_side_effect(embeddings: Iterator[list[float]], config: ProcessingConfig) -> list[Cluster]:
        if not isinstance(embeddings, (Iterator, Iterable)):
             pytest.fail("Clusterer.cluster_nodes did not receive an iterator!")
        count = sum(1 for _ in embeddings)
        if count > 1:
             return [Cluster(id=0, level=0, node_indices=list(range(count)))]
        return []
    clusterer.cluster_nodes.side_effect = cluster_nodes_side_effect
    return clusterer
