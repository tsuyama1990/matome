from collections.abc import Iterable, Iterator
from unittest.mock import MagicMock

from domain_models.config import ProcessingConfig
from domain_models.manifest import Chunk, Cluster
from matome.engines.embedder import EmbeddingService
from matome.engines.raptor import RaptorEngine
from matome.interfaces import Chunker, Clusterer, Summarizer
from matome.utils.store import DiskChunkStore


class StreamingChunker(Chunker):
    """Mock chunker that yields chunks and verifies input is not fully consumed."""

    def split_text(
        self, text: str | Iterable[str], config: ProcessingConfig
    ) -> Iterator[Chunk]:
        # Assert text is an iterator/generator, not a list
        if isinstance(text, list):
             raise AssertionError("RaptorEngine consumed the generator into a list!")  # noqa: TRY004, EM101

        for i, line in enumerate(text):
            yield Chunk(index=i, text=line, start_char_idx=0, end_char_idx=len(line))

class StreamingEmbedder(EmbeddingService):
    def embed_chunks(self, chunks: Iterable[Chunk]) -> Iterator[Chunk]:
        if isinstance(chunks, list):
             raise AssertionError("Embedder received a list!")  # noqa: TRY004, EM101
        for c in chunks:
            c.embedding = [0.1] * 10
            yield c

class StreamingClusterer(Clusterer):
    def cluster_nodes(
        self, embeddings: Iterable[list[float]], config: ProcessingConfig
    ) -> list[Cluster]:
        # GMMClusterer normally consumes embeddings to find optimal k or fit.
        # Here we just mock it to return one cluster to allow pipeline to proceed.
        # We verify embeddings is not a list if we can, but RaptorEngine passes `l0_embedding_generator()`.
        # Generators are iterators.

        # Consume strictly
        count = 0
        for _ in embeddings:
            count += 1

        return [Cluster(id=0, level=0, node_indices=list(range(count)))]

def test_raptor_streaming_input() -> None:
    """
    Verify that RaptorEngine processes an input generator without converting it to a list
    before chunking.
    """
    def text_generator() -> Iterator[str]:
        for i in range(10):
            yield f"Line {i}"

    config = ProcessingConfig()
    chunker = StreamingChunker()
    embedder = StreamingEmbedder(config)
    clusterer = StreamingClusterer()
    summarizer = MagicMock(spec=Summarizer)
    summarizer.summarize.return_value = "Summary"

    engine = RaptorEngine(chunker, embedder, clusterer, summarizer, config)

    # Run with generator
    gen = text_generator()

    # If run converts gen to list, StreamingChunker will raise AssertionError
    # Or if check_gpu reads it? No check_gpu is separate.
    # RaptorEngine.run has isinstance(text, str) check.

    with DiskChunkStore() as store:
        engine.run(gen, store=store)

    # If we reached here, no assertion error was raised.
