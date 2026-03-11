from src.domain_models import SemanticChunk
from src.interfaces import VectorDBProtocol


class MockVectorDB(VectorDBProtocol):
    """A mock implementation of a Vector Database for local testing."""

    def __init__(self) -> None:
        self.chunks: list[SemanticChunk] = []

    def store(self, chunks: list[SemanticChunk]) -> None:
        """Stores a list of semantic chunks in the mock vector database."""
        self.chunks.extend(chunks)

    def _pseudo_embed(self, text: str) -> list[float]:
        """Generates a pseudo-embedding based on deterministic word hashes for semantic similarity."""
        import hashlib
        import math
        import re

        # Extract words for semantic representation rather than characters
        words = re.findall(r"\b\w+\b", text.lower())

        # 50-dimensional fake embedding space
        dimensions = 50
        vector = [0.0] * dimensions

        if not words:
            return vector

        for word in words:
            # Use deterministic hash to map a word consistently to a specific feature dimension
            hash_val = int(hashlib.sha256(word.encode("utf-8")).hexdigest(), 16)

            # Activate 3 different dimensions per word to simulate distributed representations
            for i in range(3):
                dim = (hash_val + i * 17) % dimensions
                vector[dim] += 1.0

        # Normalize the embedding vector
        magnitude = math.sqrt(sum(x * x for x in vector))
        if magnitude == 0:
            return vector

        return [x / magnitude for x in vector]

    def _cosine_similarity(self, vec1: list[float], vec2: list[float]) -> float:
        """Calculates true cosine similarity between two mock embeddings."""
        return sum(a*b for a, b in zip(vec1, vec2, strict=True))

    def search(self, query: str, top_k: int = 5) -> list[SemanticChunk]:
        """Searches for chunks using true cosine similarity on pseudo-embeddings."""
        # Sanitize query to prevent injection into search mechanisms
        import re
        sanitized_query = re.sub(r'[^\w\s]', '', query).strip()

        if not sanitized_query:
            return []

        query_embedding = self._pseudo_embed(sanitized_query)

        scored_chunks: list[tuple[float, SemanticChunk]] = []
        for chunk in self.chunks:
            chunk_embedding = self._pseudo_embed(chunk.text)
            similarity = self._cosine_similarity(query_embedding, chunk_embedding)

            # Since vectors are positive frequencies, similarity is between 0 and 1
            if similarity > 0.1: # Minimum threshold to simulate relevance
                scored_chunks.append((similarity, chunk))

        # Sort by highest score first
        scored_chunks.sort(key=lambda x: x[0], reverse=True)

        return [chunk for score, chunk in scored_chunks[:top_k]]
