import logging

import numpy as np

from domain_models.config import ProcessingConfig
from domain_models.manifest import Chunk
from matome.engines.embedder import EmbeddingService
from matome.utils.text import iter_sentences, normalize_text

# Configure logger
logger = logging.getLogger(__name__)


def cosine_similarity(v1: list[float], v2: list[float]) -> float:
    """Calculate cosine similarity between two vectors."""
    a = np.array(v1)
    b = np.array(v2)
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(np.dot(a, b) / (norm_a * norm_b))


class JapaneseSemanticChunker:
    """
    Chunking engine that splits text based on semantic similarity.

    1. Splits text into sentences using Japanese heuristics.
    2. Embeds sentences.
    3. Merges sentences into chunks if their similarity is high,
       respecting the max_tokens limit.
    """

    def __init__(self, embedder: EmbeddingService) -> None:
        """
        Initialize with an embedding service.

        Args:
            embedder: Service to generate embeddings for sentences.
        """
        self.embedder = embedder

    def split_text(self, text: str, config: ProcessingConfig) -> list[Chunk]:
        """
        Split text into semantic chunks.

        Args:
            text: Raw input text.
            config: Configuration including semantic_chunking_threshold and max_tokens.

        Returns:
            List of Chunk objects.
        """
        if not text:
            return []

        # 1. Normalize and split into sentences
        normalized_text = normalize_text(text)
        sentences = list(iter_sentences(normalized_text))

        if not sentences:
            return []

        # 2. Embed sentences
        # Note: This might be expensive for very large documents.
        # Ideally, we should batch this or stream. But for now, we embed all.
        # Convert iterator to list for indexing
        embeddings = list(self.embedder.embed_strings(sentences))

        # 3. Merge sentences
        chunks: list[Chunk] = []
        current_chunk_sentences: list[str] = [sentences[0]]
        current_chunk_embeddings: list[list[float]] = [embeddings[0]]

        current_start_idx = 0

        for i in range(1, len(sentences)):
            sentence = sentences[i]
            embedding = embeddings[i]

            prev_embedding = current_chunk_embeddings[-1]
            similarity = cosine_similarity(prev_embedding, embedding)

            # Check size constraint (rough estimate: 1 char = 1 token for safety)
            current_text_len = sum(len(s) for s in current_chunk_sentences)

            if (similarity >= config.semantic_chunking_threshold) and (current_text_len + len(sentence) < config.max_tokens):
                current_chunk_sentences.append(sentence)
                current_chunk_embeddings.append(embedding)
            else:
                # Create chunk
                chunk_text = "".join(current_chunk_sentences)
                chunks.append(Chunk(
                    index=len(chunks),
                    text=chunk_text,
                    start_char_idx=current_start_idx,
                    end_char_idx=current_start_idx + len(chunk_text),
                    # We can optionally set the embedding of the chunk to the centroid of sentences
                    embedding=None
                ))
                current_start_idx += len(chunk_text)

                # Start new chunk
                current_chunk_sentences = [sentence]
                current_chunk_embeddings = [embedding]

        # Final chunk
        if current_chunk_sentences:
            chunk_text = "".join(current_chunk_sentences)
            chunks.append(Chunk(
                index=len(chunks),
                text=chunk_text,
                start_char_idx=current_start_idx,
                end_char_idx=current_start_idx + len(chunk_text),
                embedding=None
            ))

        return chunks
