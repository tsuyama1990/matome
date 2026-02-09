import logging
from collections.abc import Iterator

import numpy as np

from domain_models.config import ProcessingConfig
from domain_models.manifest import Chunk
from matome.engines.embedder import EmbeddingService
from matome.utils.text import iter_normalized_sentences

# Configure logger
logger = logging.getLogger(__name__)


class JapaneseSemanticChunker:
    """
    Chunking engine that splits text based on semantic similarity using a Global Percentile Strategy.

    1. Splits text into all sentences.
    2. Embeds all sentences to capture global context distribution.
    3. Calculates cosine distances between adjacent sentences on-the-fly to save memory.
    4. Determines a dynamic split threshold based on a percentile of these distances.
    5. Merges sentences into chunks where distance < threshold, respecting max_tokens.
    """

    def __init__(self, embedder: EmbeddingService) -> None:
        """
        Initialize with an embedding service.

        Args:
            embedder: Service to generate embeddings for sentences.
        """
        self.embedder = embedder

    def split_text(self, text: str, config: ProcessingConfig) -> Iterator[Chunk]:
        """
        Split text into semantic chunks using global percentile strategy.

        Args:
            text: Raw input text.
            config: Configuration including semantic_chunking_percentile and max_tokens.

        Yields:
            Chunk objects.

        Raises:
            ValueError: If input text is not a string.
        """
        self._validate_input(text)

        if not text:
            return

        # 1. Collect all sentences (Normalization)
        sentences = list(iter_normalized_sentences(text))
        if not sentences:
            return

        # Handle single sentence case immediately
        if len(sentences) == 1:
            yield Chunk(
                index=0,
                text=sentences[0],
                start_char_idx=0,
                end_char_idx=len(sentences[0]),
                embedding=None,
            )
            return

        # 2. Calculate Distances
        distances = self._calculate_semantic_distances(sentences)
        if not distances:
            # Should not happen given len > 1, but safety fallback
            yield Chunk(
                index=0,
                text=sentences[0],
                start_char_idx=0,
                end_char_idx=len(sentences[0]),
                embedding=None,
            )
            return

        # 3. Create Chunks
        yield from self._create_chunks(sentences, distances, config)

    def _calculate_semantic_distances(self, sentences: list[str]) -> list[float]:
        """
        Stream embeddings and calculate cosine distances between adjacent sentences.
        Returns a list of distances.
        """
        distances: list[float] = []
        prev_embedding: np.ndarray | None = None

        try:
            # embed_strings streams embeddings
            for embedding_list in self.embedder.embed_strings(sentences):
                current_embedding = np.array(embedding_list)

                if prev_embedding is not None:
                    # Calculate Cosine Distance = 1 - Cosine Similarity
                    norm_a = np.linalg.norm(prev_embedding)
                    norm_b = np.linalg.norm(current_embedding)

                    if norm_a == 0 or norm_b == 0:
                        sim = 0.0
                    else:
                        sim = float(np.dot(prev_embedding, current_embedding) / (norm_a * norm_b))

                    # Clamp sim to [-1, 1]
                    sim = max(-1.0, min(1.0, sim))
                    distances.append(1.0 - sim)

                prev_embedding = current_embedding

        except Exception:
            logger.exception("Failed to generate embeddings for sentences.")
            raise

        return distances

    def _create_chunks(
        self, sentences: list[str], distances: list[float], config: ProcessingConfig
    ) -> Iterator[Chunk]:
        """
        Merge sentences into chunks based on semantic distance threshold.
        """
        percentile_val = config.semantic_chunking_percentile
        threshold = np.percentile(distances, percentile_val)

        logger.info(
            f"Global Semantic Chunking: Calculated threshold {threshold:.4f} at {percentile_val}th percentile."
        )

        current_chunk_sentences: list[str] = [sentences[0]]
        current_chunk_len = len(sentences[0])
        current_start_idx = 0
        current_chunk_index = 0

        # Iterate gaps. distances[i] is gap between sentences[i] and sentences[i+1]
        for i, dist in enumerate(distances):
            next_sentence = sentences[i + 1]
            next_len = len(next_sentence)

            is_semantic_break = dist > threshold
            is_token_overflow = (current_chunk_len + next_len) > config.max_tokens

            if is_semantic_break or is_token_overflow:
                # Finalize current chunk
                chunk_text = "".join(current_chunk_sentences)
                yield Chunk(
                    index=current_chunk_index,
                    text=chunk_text,
                    start_char_idx=current_start_idx,
                    end_char_idx=current_start_idx + len(chunk_text),
                    embedding=None,
                )

                # Reset for next chunk
                current_chunk_index += 1
                current_start_idx += len(chunk_text)
                current_chunk_sentences = [next_sentence]
                current_chunk_len = next_len
            else:
                # Merge
                current_chunk_sentences.append(next_sentence)
                current_chunk_len += next_len

        # Final flush
        if current_chunk_sentences:
            chunk_text = "".join(current_chunk_sentences)
            yield Chunk(
                index=current_chunk_index,
                text=chunk_text,
                start_char_idx=current_start_idx,
                end_char_idx=current_start_idx + len(chunk_text),
                embedding=None,
            )

    def _validate_input(self, text: str) -> None:
        if not isinstance(text, str):
            msg = f"Input text must be a string, got {type(text)}."
            raise TypeError(msg)
