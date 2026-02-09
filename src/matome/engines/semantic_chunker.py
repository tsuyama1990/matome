import logging
from collections.abc import Iterator
from typing import cast

import numpy as np

from domain_models.config import ProcessingConfig
from domain_models.manifest import Chunk
from matome.engines.embedder import EmbeddingService
from matome.utils.text import iter_normalized_sentences

# Configure logger
logger = logging.getLogger(__name__)


def calculate_cosine_distances(embeddings: list[list[float]]) -> list[float]:
    """
    Calculate cosine distances (1 - similarity) between adjacent embeddings.
    Returns a list of length N-1.
    """
    if len(embeddings) < 2:
        return []

    matrix = np.array(embeddings)
    norms = np.linalg.norm(matrix, axis=1)

    # Avoid division by zero
    norms[norms == 0] = 1e-10

    normalized_matrix = matrix / norms[:, np.newaxis]

    # Calculate dot products of adjacent vectors: v[i] dot v[i+1]
    similarities = np.sum(normalized_matrix[:-1] * normalized_matrix[1:], axis=1)

    # Distance is 1 - Similarity.
    # Range is [0, 2] because cosine sim is [-1, 1].
    distances = 1.0 - similarities
    return cast(list[float], distances.tolist())


class JapaneseSemanticChunker:
    """
    Chunking engine that splits text based on semantic similarity using a Global Percentile Strategy.

    1. Splits text into all sentences.
    2. Embeds all sentences to capture global context distribution.
    3. Calculates cosine distances between adjacent sentences.
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

        # 2. Embed all sentences
        try:
            # We consume the iterator into a list because we need random access / all items
            embeddings = list(self.embedder.embed_strings(sentences))
        except Exception:
            logger.exception("Failed to generate embeddings for sentences.")
            raise

        if len(sentences) != len(embeddings):
            logger.warning(
                f"Mismatch between sentences ({len(sentences)}) and embeddings ({len(embeddings)})."
            )
            # Proceed with the shorter length to avoid crashing
            min_len = min(len(sentences), len(embeddings))
            sentences = sentences[:min_len]
            embeddings = embeddings[:min_len]

        if len(sentences) == 1:
            # Single sentence case
            yield Chunk(
                index=0,
                text=sentences[0],
                start_char_idx=0,
                end_char_idx=len(sentences[0]),
                embedding=None,
            )
            return

        # 3. Calculate Distances & Threshold
        distances = calculate_cosine_distances(embeddings)

        # Calculate dynamic threshold
        # If percentile is 90, we want to split at the top 10% largest distances (most dissimilar).
        # So we look for the 90th percentile value.
        # Any distance > threshold is a breakpoint.
        percentile_val = config.semantic_chunking_percentile
        threshold = np.percentile(distances, percentile_val)

        logger.info(f"Global Semantic Chunking: Calculated threshold {threshold:.4f} at {percentile_val}th percentile.")

        # 4. Merge Sentences
        current_chunk_sentences: list[str] = [sentences[0]]
        current_chunk_len = len(sentences[0])
        current_start_idx = 0
        current_chunk_index = 0

        # We iterate through the gaps between sentences.
        # gap i is between sentence i and sentence i+1.
        # distance[i] corresponds to gap i.

        for i in range(len(distances)):
            dist = distances[i]
            next_sentence = sentences[i+1]
            next_len = len(next_sentence)

            # Logic:
            # If distance > threshold, it's a semantic break -> Split.
            # OR if adding next sentence exceeds max_tokens -> Split.
            # Else -> Merge.

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
