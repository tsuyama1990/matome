import itertools
import logging
from collections.abc import Iterable, Iterator

import numpy as np
from sentence_transformers import SentenceTransformer

from domain_models.config import ProcessingConfig
from domain_models.manifest import Chunk

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
        # Initialize the model immediately (load weights)
        logger.info(f"Loading embedding model: {self.model_name}")
        self.model = SentenceTransformer(self.model_name)

    def embed_strings(self, texts: Iterable[str]) -> Iterator[list[float]]:
        """
        Embeds an iterable of strings and yields their vectors.

        This method processes inputs in batches to avoid loading all texts or embeddings into memory.
        Uses itertools.batched for efficient streaming.

        Args:
            texts: Iterable of strings to embed.

        Yields:
            Embedding vectors (lists of floats).
        """
        batch_size = self.config.embedding_batch_size

        # Use itertools.batched (Python 3.12+) for memory-safe batching
        for batch in itertools.batched(texts, batch_size):
            # batch is a tuple of strings
            yield from self._process_batch(list(batch))

    def _process_batch(self, batch_texts: list[str]) -> Iterator[list[float]]:
        """Helper to process a single batch."""
        if not batch_texts:
            return

        try:
            batch_embeddings = self.model.encode(
                batch_texts,
                batch_size=len(batch_texts), # We already batched it manually
                convert_to_numpy=True,
                show_progress_bar=False
            )

            if isinstance(batch_embeddings, np.ndarray):
                # Iterate over rows
                for i in range(batch_embeddings.shape[0]):
                    yield batch_embeddings[i].tolist()
            else:
                # List of tensors or arrays
                for emb in batch_embeddings:
                     yield emb.tolist()

        except Exception:
            logger.exception("Failed to encode batch.")
            raise

    def embed_chunks(self, chunks: list[Chunk]) -> list[Chunk]:
        """
        Embeds a list of chunks in-place and returns them.
        """
        if not chunks:
            return []

        # Create a generator for texts
        texts_gen = (chunk.text for chunk in chunks)

        # consume the generator
        embeddings_gen = self.embed_strings(texts_gen)

        for chunk, embedding in zip(chunks, embeddings_gen, strict=True):
            chunk.embedding = embedding

        return chunks
