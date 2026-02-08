import logging
from collections.abc import Iterable, Iterator

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
            config: Processing configuration containing `embedding` settings.
        """
        self.config = config
        self.model_name = config.embedding.model_name
        # Initialize the model immediately (load weights)
        logger.info(f"Loading embedding model: {self.model_name}")
        self.model = SentenceTransformer(self.model_name)

    def embed_chunks(self, chunks: Iterable[Chunk]) -> Iterator[Chunk]:
        """
        Embeds a stream of chunks and returns them as an iterator.

        This method processes chunks in batches to avoid high memory usage.
        It yields chunks immediately after processing each batch.

        Args:
            chunks: Iterable of Chunk objects to embed.

        Returns:
            Iterator of Chunk objects with 'embedding' field populated.
        """
        batch_size = self.config.embedding.batch_size
        current_batch: list[Chunk] = []

        logger.debug(f"Generating embeddings with batch_size={batch_size}")

        for chunk in chunks:
            current_batch.append(chunk)

            if len(current_batch) >= batch_size:
                yield from self._process_batch(current_batch)
                current_batch = []

        # Process remaining chunks
        if current_batch:
            yield from self._process_batch(current_batch)

    def _process_batch(self, batch: list[Chunk]) -> Iterator[Chunk]:
        """Helper to embed a single batch of chunks."""
        texts = [chunk.text for chunk in batch]

        try:
            # encode returns a numpy array or list of numpy arrays
            batch_embeddings = self.model.encode(
                texts,
                batch_size=len(batch), # We already batched it
                convert_to_numpy=True,
                show_progress_bar=False
            )

            # Assign immediately to chunks in this batch
            for chunk, embedding in zip(batch, batch_embeddings, strict=True):
                chunk.embedding = embedding.tolist()
                yield chunk

        except Exception:
            # We could log more specific details here
            logger.exception("Failed to encode batch")
            raise

    def embed_strings(self, texts: list[str]) -> list[list[float]]:
        """
        Embeds a list of strings and returns their vectors.
        Useful for Semantic Chunking where we need to embed sentences before creating Chunks.

        Args:
            texts: List of strings to embed.

        Returns:
            List of embeddings (each is a list of floats).
        """
        if not texts:
            return []

        try:
            # encode returns a numpy array or list of numpy arrays
            # We use the configured batch size
            embeddings = self.model.encode(
                texts,
                batch_size=self.config.embedding.batch_size,
                convert_to_numpy=True,
                show_progress_bar=False
            )
            # Convert to list of lists
            return [emb.tolist() for emb in embeddings]
        except Exception:
            logger.exception("Failed to encode strings")
            raise
