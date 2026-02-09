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
    Chunking engine that splits text based on semantic similarity using a global percentile threshold.

    1. Splits text into sentences using Japanese heuristics (constants.SENTENCE_SPLIT_PATTERN).
    2. Embeds ALL sentences to capture global context distribution.
    3. Calculates cosine similarity between adjacent sentences.
    4. Determines a split threshold based on the configured percentile of distances.
    5. Merges sentences into chunks until the threshold is met or max_tokens is reached.
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
        Split text into semantic chunks.

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

        # 1. Get all normalized sentences
        # We need the full list to calculate global percentile
        sentences = list(iter_normalized_sentences(text))
        if not sentences:
            return

        n_sentences = len(sentences)

        # Edge Case: Single sentence -> Single chunk
        if n_sentences == 1:
            yield self._create_chunk(0, sentences[0], 0)
            return

        # 2. Generate embeddings for all sentences
        # embed_strings returns an iterator, consume it all
        try:
            embeddings_iter = self.embedder.embed_strings(sentences)
            embeddings = list(embeddings_iter)
        except Exception:
            logger.exception("Failed to generate embeddings for sentences.")
            raise

        if len(embeddings) != n_sentences:
            msg = f"Mismatch: {n_sentences} sentences but {len(embeddings)} embeddings."
            logger.error(msg)
            # Proceed carefully or raise? Raising is safer.
            raise ValueError(msg)

        # 3. Calculate Similarities & Threshold
        distances = self._calculate_distances(embeddings)

        # Calculate threshold based on percentile
        # config.semantic_chunking_percentile (e.g., 90)
        # We split if distance > threshold
        percentile = float(config.semantic_chunking_percentile)
        threshold = np.percentile(distances, percentile)

        logger.info(
            f"Semantic Chunking: {n_sentences} sentences. "
            f"Percentile={percentile}, Threshold (Dist)={threshold:.4f}"
        )

        # 4. Merge Sentences
        current_chunk_sentences: list[str] = []
        current_chunk_len = 0
        current_start_idx = 0
        chunk_index = 0

        # We iterate through sentences. The i-th distance corresponds to gap between sentence i and i+1.
        # distances[i] is distance between sentences[i] and sentences[i+1]

        for i, sentence in enumerate(sentences):
            current_chunk_sentences.append(sentence)
            current_chunk_len += len(sentence)

            # Determine if we should split AFTER this sentence
            # We can only split if there is a next sentence (i < n_sentences - 1)
            if i < n_sentences - 1:
                dist = distances[i]
                should_split = dist > threshold

                # Also check max_tokens limit (hard limit)
                # If adding the NEXT sentence would exceed max_tokens, we MUST split now?
                # Or we check if current is already too big?
                # Usually we check before adding, or check if accumulating.
                # Here we check: If we DON'T split, the chunk grows.
                # Let's check if the *current* chunk is getting too big relative to max_tokens?
                # Or better: check if adding next sentence would overflow.

                next_len = len(sentences[i+1])
                will_overflow = (current_chunk_len + next_len) > config.max_tokens

                if should_split or will_overflow:
                    # Commit current chunk
                    chunk_text = "".join(current_chunk_sentences)
                    yield self._create_chunk(chunk_index, chunk_text, current_start_idx)

                    chunk_index += 1
                    current_start_idx += len(chunk_text)
                    current_chunk_sentences = []
                    current_chunk_len = 0
            else:
                # Last sentence. Always commit what we have.
                pass

        # Final flush
        if current_chunk_sentences:
            chunk_text = "".join(current_chunk_sentences)
            yield self._create_chunk(chunk_index, chunk_text, current_start_idx)

    def _calculate_distances(self, embeddings: list[list[float]]) -> np.ndarray:
        """
        Calculate cosine distances (1 - similarity) between adjacent embeddings.
        Returns array of shape (N-1,).
        """
        # Convert to numpy array
        matrix = np.array(embeddings)

        # Normalize rows
        norms = np.linalg.norm(matrix, axis=1, keepdims=True)
        norms[norms == 0] = 1e-10  # Avoid division by zero
        normalized = matrix / norms

        # Calculate cosine similarity between adjacent vectors
        # dot product of i and i+1
        # normalized[:-1] is 0..N-2
        # normalized[1:] is 1..N-1
        similarities = np.sum(normalized[:-1] * normalized[1:], axis=1)

        # Clip to [-1, 1] to avoid numerical errors
        similarities = np.clip(similarities, -1.0, 1.0)

        # Distance = 1 - Similarity
        return 1.0 - similarities

    def _create_chunk(self, index: int, text: str, start_char_idx: int) -> Chunk:
        """Helper to create a Chunk object."""
        return Chunk(
            index=index,
            text=text,
            start_char_idx=start_char_idx,
            end_char_idx=start_char_idx + len(text),
            embedding=None,  # Embeddings for chunks will be generated later by RaptorEngine L0
        )

    def _validate_input(self, text: str) -> None:
        if not isinstance(text, str):
            msg = f"Input text must be a string, got {type(text)}."
            raise TypeError(msg)
