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
        """Searches for chunks using a mock semantic similarity algorithm (TF-IDF proxy)."""
        import math
        import re
        from collections import Counter

        def tokenize(text: str) -> list[str]:
            """Simple tokenization removing punctuation."""
            return re.findall(r"\b\w+\b", text.lower())

        query_tokens = tokenize(query)
        if not query_tokens:
            return []

        # Calculate document frequencies
        doc_freqs: Counter[str] = Counter()
        tokenized_chunks = []

        for chunk in self.chunks:
            tokens = tokenize(chunk.text)
            tokenized_chunks.append((chunk, tokens))
            for unique_token in set(tokens):
                doc_freqs[unique_token] += 1

        total_docs = len(self.chunks)
        if total_docs == 0:
            return []

        # Calculate TF-IDF scores
        scored_chunks: list[tuple[float, SemanticChunk]] = []
        for chunk, tokens in tokenized_chunks:
            tf = Counter(tokens)
            score = 0.0

            for q_token in query_tokens:
                if q_token in tf:
                    # Term Frequency
                    term_freq = tf[q_token]
                    # Inverse Document Frequency (add 1 to avoid div by zero)
                    idf = math.log(total_docs / (1 + doc_freqs[q_token])) + 1
                    score += term_freq * idf

            if score > 0:
                scored_chunks.append((score, chunk))

        # Sort by highest score first
        scored_chunks.sort(key=lambda x: x[0], reverse=True)

        return [chunk for score, chunk in scored_chunks[:top_k]]
