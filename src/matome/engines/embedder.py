import logging

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

    def embed_strings(self, texts: list[str]) -> list[list[float]]:
        """
        Embeds a list of strings and returns their vectors.

        Args:
            texts: List of strings to embed.

        Returns:
            List of embedding vectors (lists of floats).
        """
        if not texts:
            return []

        batch_size = self.config.embedding_batch_size
        all_embeddings: list[list[float]] = []

        logger.debug(f"Generating embeddings for {len(texts)} strings with batch_size={batch_size}")

        for i in range(0, len(texts), batch_size):
            batch_texts = texts[i : i + batch_size]
            try:
                batch_embeddings = self.model.encode(
                    batch_texts,
                    batch_size=batch_size,
                    convert_to_numpy=True,
                    show_progress_bar=False
                )
                if isinstance(batch_embeddings, np.ndarray):
                     all_embeddings.extend(batch_embeddings.tolist())
                else:
                     # Fallback if list returned (rare with convert_to_numpy=True)
                     all_embeddings.extend([e.tolist() for e in batch_embeddings])

            except Exception:
                logger.exception(f"Failed to encode batch starting at index {i}")
                raise

        return all_embeddings

    def embed_chunks(self, chunks: list[Chunk]) -> list[Chunk]:
        """
        Embeds a list of chunks in-place and returns them.
        """
        if not chunks:
            return []

        texts = [chunk.text for chunk in chunks]
        embeddings = self.embed_strings(texts)

        for chunk, embedding in zip(chunks, embeddings, strict=True):
            chunk.embedding = embedding

        return chunks
