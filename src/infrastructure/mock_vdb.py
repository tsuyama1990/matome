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
        """Searches for chunks that contain the query string (mock similarity search)."""
        results = [chunk for chunk in self.chunks if query in chunk.text]
        return results[:top_k]
