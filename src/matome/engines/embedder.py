import logging

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
        It assigns embeddings to chunks immediately after processing each batch
        to avoid accumulating a massive embeddings array in memory.

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

        for i in range(0, len(texts), batch_size):
            batch_texts = texts[i : i + batch_size]
            batch_chunks = chunks[i : i + batch_size]

            try:
                # encode returns a numpy array or list of numpy arrays
                batch_embeddings = self.model.encode(
                    batch_texts,
                    batch_size=batch_size,
                    convert_to_numpy=True,
                    show_progress_bar=False
                )

                # Assign immediately to chunks in this batch
                for chunk, embedding in zip(batch_chunks, batch_embeddings, strict=True):
                    chunk.embedding = embedding.tolist()

            except Exception:
                logger.exception(f"Failed to encode batch starting at index {i}")
                raise

        return chunks
