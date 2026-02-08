from sentence_transformers import SentenceTransformer

from domain_models.manifest import Chunk


class EmbeddingService:
    """Service for generating vector embeddings for chunks."""

    def __init__(self, model_name: str = "intfloat/multilingual-e5-large") -> None:
        """
        Initialize the embedding service.

        Args:
            model_name: The name of the HuggingFace model to use.
        """
        self.model_name = model_name
        # Initialize the model immediately (load weights)
        self.model = SentenceTransformer(model_name)

    def embed_chunks(self, chunks: list[Chunk]) -> list[Chunk]:
        """
        Embeds a list of chunks in-place and returns them.

        Args:
            chunks: List of Chunk objects to embed.

        Returns:
            The input list of Chunk objects with 'embedding' field populated.
        """
        if not chunks:
            return []

        texts = [chunk.text for chunk in chunks]
        # Calculate embeddings for all texts in batch
        # convert_to_numpy=True returns ndarray, we want list[float]
        embeddings = self.model.encode(texts, convert_to_numpy=True)

        # Assign embeddings back to chunks
        for chunk, embedding in zip(chunks, embeddings, strict=True):
            chunk.embedding = embedding.tolist()

        return chunks
