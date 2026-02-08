import logging

import numpy as np
from sentence_transformers import SentenceTransformer

from domain_models.config import ProcessingConfig
from domain_models.manifest import Chunk

logger = logging.getLogger(__name__)

class EmbeddingService:
    """Service for generating vector embeddings for chunks."""

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

    def embed_chunks(self, chunks: list[Chunk]) -> list[Chunk]:
        """
        Embeds a list of chunks in-place and returns them.

        This method processes chunks in batches to avoid high memory usage.

        Args:
            chunks: List of Chunk objects to embed.

        Returns:
            The input list of Chunk objects with 'embedding' field populated.
        """
        if not chunks:
            return []

        texts = [chunk.text for chunk in chunks]
        batch_size = self.config.embedding_batch_size

        logger.debug(f"Generating embeddings for {len(chunks)} chunks with batch_size={batch_size}")

        # Calculate embeddings in batches
        all_embeddings = []
        for i in range(0, len(texts), batch_size):
            batch_texts = texts[i : i + batch_size]
            # model.encode supports batch_size too, but explicit loop gives more control if needed
            # sentence-transformers encode handles batching internally if we pass batch_size parameter,
            # but slicing here ensures we control the input list size too.
            # Actually, encode takes full list and `batch_size` param.
            # However, providing a massive list to `encode` still creates a massive tokenized input.
            # So explicit slicing is safer for extremely large inputs.
            try:
                batch_embeddings = self.model.encode(
                    batch_texts,
                    batch_size=batch_size,
                    convert_to_numpy=True,
                    show_progress_bar=False
                )
                all_embeddings.append(batch_embeddings)
            except Exception:
                logger.exception(f"Failed to encode batch starting at index {i}")
                raise

        # Concatenate all batches
        final_embeddings = np.vstack(all_embeddings) if all_embeddings else np.array([])

        # Assign embeddings back to chunks
        for chunk, embedding in zip(chunks, final_embeddings, strict=True):
            chunk.embedding = embedding.tolist()

        return chunks
