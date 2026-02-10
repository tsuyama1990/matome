import logging
from collections.abc import Iterable, Iterator

import numpy as np
from sentence_transformers import SentenceTransformer

from domain_models.config import ProcessingConfig
from domain_models.manifest import Chunk
from matome.utils.compat import batched

logger = logging.getLogger(__name__)


class EmbeddingService:
    """Service for generating vector embeddings for text and chunks."""

    def __init__(self, config: ProcessingConfig) -> None:
        """
        Initialize the embedding service.

        Args:
            config: Processing configuration containing `embedding_model` and `embedding_batch_size`.
        """
        self.config = config
        self.model_name = config.embedding_model
        # Lazy loading: Do not initialize model here.
        self._model: SentenceTransformer | None = None

    @property
    def model(self) -> SentenceTransformer:
        """Lazy loader for the SentenceTransformer model."""
        if self._model is None:
            logger.info(f"Loading embedding model: {self.model_name}")
            self._model = SentenceTransformer(self.model_name)
        return self._model

    def embed_strings(self, texts: Iterable[str]) -> Iterator[list[float]]:
        """
        Embeds an iterable of strings and yields their vectors.

        This method processes inputs in batches to avoid loading all texts or embeddings into memory.
        Uses batched utility (Python 3.12+ compatible) for efficient streaming.

        Args:
            texts: Iterable of strings to embed.

        Yields:
            Embedding vectors (lists of floats).
        """
        batch_size = self.config.embedding_batch_size
        processed_count = 0

        # Use batched utility for memory-safe batching
        for batch in batched(texts, batch_size):
            processed_count += len(batch)
            if processed_count % (batch_size * 10) == 0:
                logger.info(f"Embedded {processed_count} items...")

            # batch is a tuple of strings
            yield from self._process_batch(batch)

    def _process_batch(self, batch_texts: list[str] | tuple[str, ...]) -> Iterator[list[float]]:
        """Helper to process a single batch."""
        if not batch_texts:
            return

        try:
            # Access self.model (property) to trigger lazy load if needed
            # Process in strict mini-batches to avoid any large memory allocation
            # SentenceTransformer.encode internally batches, but returns full result.
            # We must call encode on smaller chunks if we want to avoid full result in memory.
            MINI_BATCH_SIZE = 8

            for i in range(0, len(batch_texts), MINI_BATCH_SIZE):
                chunk_texts = batch_texts[i : i + MINI_BATCH_SIZE]  # slice works on list/tuple

                chunk_embeddings = self.model.encode(
                    chunk_texts,
                    batch_size=len(chunk_texts),
                    convert_to_numpy=True,
                    show_progress_bar=False,
                )

                if isinstance(chunk_embeddings, np.ndarray):
                    for j in range(chunk_embeddings.shape[0]):
                        yield chunk_embeddings[j].tolist()
                else:
                    for emb in chunk_embeddings:
                        yield emb.tolist()

        except Exception:
            logger.exception("Failed to encode batch.")
            raise

    def embed_chunks(self, chunks: Iterable[Chunk]) -> Iterator[Chunk]:
        """
        Embeds an iterable of chunks and yields them with embeddings.
        This enables streaming processing of chunks.
        """
        batch_size = self.config.embedding_batch_size

        # Use batched utility to stream chunks in batches
        for batch_chunks in batched(chunks, batch_size):
            # batch_chunks is a tuple of Chunk objects
            texts = [c.text for c in batch_chunks]

            # Embed batch (returns iterator, consumed immediately)
            embeddings_gen = self._process_batch(texts)

            # Assign and yield
            for chunk, embedding in zip(batch_chunks, embeddings_gen, strict=True):
                chunk.embedding = embedding
                yield chunk
