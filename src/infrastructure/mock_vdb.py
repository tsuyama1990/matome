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
        """Generates a pseudo-embedding for the text based on character frequencies."""
        # This acts as a mock embedding vector space of size 26 (A-Z frequencies)
        # It provides a true cosine similarity calculation across text inputs to satisfy architectural requirements.
        import string

        counts = dict.fromkeys(string.ascii_lowercase, 0)
        for char in text.lower():
            if char in counts:
                counts[char] += 1

        # Return as normalized vector
        import math
        vector = list(counts.values())
        magnitude = math.sqrt(sum(x*x for x in vector))
        if magnitude == 0:
            return [0.0] * 26
        return [x/magnitude for x in vector]

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
