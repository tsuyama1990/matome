from src.domain_models import SemanticChunk
from src.interfaces import VectorDBProtocol


class MockVectorDB(VectorDBProtocol):
    """A mock implementation of a Vector Database for local testing."""

    def __init__(self) -> None:
        self.chunks: list[SemanticChunk] = []

    def store(self, chunks: list[SemanticChunk]) -> None:
        """Stores a list of semantic chunks in the mock vector database."""
        self.chunks.extend(chunks)

    def search(self, query: str, top_k: int = 5) -> list[SemanticChunk]:
        """Searches for chunks using a mock semantic similarity algorithm."""
        # Split query into words for simple pseudo TF-IDF matching
        query_words = set(query.lower().split())

        scored_chunks: list[tuple[float, SemanticChunk]] = []
        for chunk in self.chunks:
            chunk_words = set(chunk.text.lower().split())

            # Calculate Jaccard-like similarity as a proxy for semantic search
            intersection = query_words.intersection(chunk_words)
            union = query_words.union(chunk_words)

            if not union:
                continue

            score = len(intersection) / len(union)
            if score > 0:
                scored_chunks.append((score, chunk))

        # Sort by highest score first
        scored_chunks.sort(key=lambda x: x[0], reverse=True)

        return [chunk for score, chunk in scored_chunks[:top_k]]
