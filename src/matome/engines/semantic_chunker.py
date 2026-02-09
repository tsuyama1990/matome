import itertools
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
    2. Embeds sentences (streaming).
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

        This implementation streams sentences and embeddings to minimize memory usage,
        avoiding materialization of all sentence embeddings at once.

        Args:
            text: Raw input text.
            config: Configuration including semantic_chunking_threshold and max_tokens.

        Returns:
            List of Chunk objects.
        """
        if not text:
            return []

        # 1. Normalize and stream sentences
        normalized_text = normalize_text(text)
        sentences_gen = iter_sentences(normalized_text)

        # Create two iterators: one for embedding, one for content
        sentences_for_embedding, sentences_for_content = itertools.tee(sentences_gen, 2)

        # 2. Embed sentences (lazy generator)
        # Ensure we have an iterator (handles mocks returning lists)
        embeddings_gen = iter(self.embedder.embed_strings(sentences_for_embedding))

        # 3. Stream processing
        chunks: list[Chunk] = []

        # Initialize state with the first sentence
        try:
            first_sentence = next(sentences_for_content)
            first_embedding = next(embeddings_gen)
        except StopIteration:
            return []

        current_chunk_sentences: list[str] = [first_sentence]
        # We only need the latest embedding to compare with the next one
        # But if we want to calculate centroid later, we might need all.
        # For simple splitting, we compare adjacent sentences.
        # RAPTOR/Semantic Chunking usually compares current sentence with *current chunk* or *previous sentence*.
        # The original implementation compared with *previous sentence embedding*.
        current_last_embedding = first_embedding

        current_start_idx = 0

        # Iterate through the rest
        for sentence, embedding in zip(sentences_for_content, embeddings_gen, strict=True):
            similarity = cosine_similarity(current_last_embedding, embedding)

            # Check size constraint (rough estimate: 1 char = 1 token for safety/speed)
            current_text_len = sum(len(s) for s in current_chunk_sentences)

            # Determine whether to merge the current sentence into the existing chunk
            if (similarity >= config.semantic_chunking_threshold) and (current_text_len + len(sentence) < config.max_tokens):
                current_chunk_sentences.append(sentence)
                current_last_embedding = embedding
            else:
                # Create chunk from accumulated sentences
                chunk_text = "".join(current_chunk_sentences)
                chunks.append(Chunk(
                    index=len(chunks),
                    text=chunk_text,
                    start_char_idx=current_start_idx,
                    end_char_idx=current_start_idx + len(chunk_text),
                    # We don't store sentence embeddings to save memory.
                    # If chunk embedding is needed, it should be calculated for the whole chunk later.
                    embedding=None
                ))
                current_start_idx += len(chunk_text)

                # Start new chunk with current sentence
                current_chunk_sentences = [sentence]
                current_last_embedding = embedding

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
