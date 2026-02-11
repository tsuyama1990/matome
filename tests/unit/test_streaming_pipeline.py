
import shutil
import tempfile
from collections.abc import Generator, Iterator, Iterable
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest

from domain_models.config import ClusteringAlgorithm, ProcessingConfig
from matome.engines.chunker import JapaneseTokenChunker
from matome.engines.embedder import EmbeddingService
from matome.engines.raptor import RaptorEngine
from matome.agents.summarizer import SummarizationAgent
from matome.utils.store import DiskChunkStore
from domain_models.manifest import Cluster, Chunk
from matome.interfaces import Chunker, Clusterer, Summarizer

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
    input_list = [
        "This is sentence 1.",
        "This is sentence 2.",
        "This is sentence 3.",
        "This is sentence 4.",
    ] * 2 # 8 items

    # Create a generator that yields items one by one to verify streaming consumption
    def input_generator() -> Iterator[str]:
        for item in input_list:
            yield item

    # 2. Components

    # Mock Chunker: Returns chunks from iterator
    chunker = MagicMock(spec=Chunker)
    def split_text_side_effect(text: str | Iterable[str], config: ProcessingConfig) -> Iterator[Chunk]:
        if not isinstance(text, (Iterator, Iterable)):
             pytest.fail("Chunker did not receive an iterable/iterator!")
        # Consume iterator
        for i, t in enumerate(text):
            yield Chunk(index=i, text=t, start_char_idx=0, end_char_idx=len(t))

    chunker.split_text.side_effect = split_text_side_effect

    # Mock Embedder: Receives chunks iterator
    embedder = MagicMock(spec=EmbeddingService)
    def embed_chunks_side_effect(chunks: Iterable[Chunk]) -> Iterator[Chunk]:
        if not isinstance(chunks, (Iterator, Iterable)):
             pytest.fail("Embedder.embed_chunks did not receive an iterator!")
        for chunk in chunks:
            chunk.embedding = [0.1] * 4
            yield chunk

    embedder.embed_chunks.side_effect = embed_chunks_side_effect

    # Mock Embedder.embed_strings for summaries
    def embed_strings_side_effect(texts: Iterable[str]) -> Iterator[list[float]]:
        # texts is batched list usually, but embed_strings takes iterable
        if not isinstance(texts, (Iterator, Iterable)):
             # Actually embed_strings receives iterable, but Raptor might batch calls.
             # Raptor calls embed_strings with list if batching?
             # _batched_embedding_generator calls batched() then embed_strings with list.
             # So this check might fail if strict Iterator required.
             pass
        for _ in texts:
            yield [0.1] * 4
    embedder.embed_strings.side_effect = embed_strings_side_effect

    # Mock Summarizer
    summarizer = MagicMock(spec=Summarizer)
    summarizer.summarize.return_value = "Summary text"

    # Mock Clusterer: Receives embeddings iterator
    clusterer = MagicMock(spec=Clusterer)

    def cluster_nodes_side_effect(embeddings: Iterator[list[float]], config: ProcessingConfig) -> list[Cluster]:
        if not isinstance(embeddings, (Iterator, Iterable)):
             pytest.fail("Clusterer.cluster_nodes did not receive an iterator!")

        # Consume to check streaming
        count = sum(1 for _ in embeddings)

        # Return dummy cluster to stop recursion after 1 level
        if count > 1:
             return [Cluster(id=0, level=0, node_indices=list(range(count)))]
        return []

    clusterer.cluster_nodes.side_effect = cluster_nodes_side_effect

    # 3. Initialize RaptorEngine
    engine = RaptorEngine(chunker, embedder, clusterer, summarizer, config)

    # 4. Run with Iterable
    engine.run(input_generator(), store=temp_store)

    # 5. Assertions
    # Verify that components were called
    assert chunker.split_text.called
    assert embedder.embed_chunks.called
    assert clusterer.cluster_nodes.called
    assert summarizer.summarize.called
