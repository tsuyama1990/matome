import logging
from collections.abc import Iterable, Iterator

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
    Optimized for memory safety by using a two-pass approach to avoid loading full text.

    Pass 1: Stream sentences -> Embed -> Calculate Distances (store floats only).
    Pass 2: Stream sentences -> Chunk based on stored distances and threshold.
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

        # Pass 1: Calculate Distances (Consumes text stream once)
        # We need to recreate the iterator for each pass
        distances = self._calculate_semantic_distances(iter_normalized_sentences(text))

        if not distances:
            # Handle single sentence or empty case
            # We need to peek at least one sentence to be sure
            sentences_iter = iter_normalized_sentences(text)
            first_sentence = next(sentences_iter, None)
            if first_sentence:
                yield Chunk(
                    index=0,
                    text=first_sentence,
                    start_char_idx=0,
                    end_char_idx=len(first_sentence),
                    embedding=None,
                )
            return

        # Calculate Threshold
        percentile_val = config.semantic_chunking_percentile
        threshold = float(np.percentile(distances, percentile_val))

        logger.info(
            f"Global Semantic Chunking: Calculated threshold {threshold:.4f} at {percentile_val}th percentile."
        )

        # Pass 2: Chunking (Consumes text stream again)
        sentences_iter_2 = iter_normalized_sentences(text)
        yield from self._create_chunks(sentences_iter_2, distances, threshold, config)

    def _calculate_semantic_distances(self, sentences: Iterable[str]) -> list[float]:
        """
        Stream embeddings and calculate cosine distances between adjacent sentences.
        Returns a list of distances (floats).
        """
        distances: list[float] = []
        prev_embedding: np.ndarray | None = None

        try:
            # embed_strings streams embeddings
            for embedding_list in self.embedder.embed_strings(sentences):
                current_embedding = np.array(embedding_list)

                if prev_embedding is not None:
                    # Validate Dimension Consistency
                    self._validate_dimensions(prev_embedding, current_embedding)

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
        self,
        sentences: Iterator[str],
        distances: list[float],
        threshold: float,
        config: ProcessingConfig,
    ) -> Iterator[Chunk]:
        """
        Merge sentences into chunks based on semantic distance threshold.
        """
        try:
            first_sentence = next(sentences)
        except StopIteration:
            return

        current_chunk_sentences: list[str] = [first_sentence]
        current_chunk_len = len(first_sentence)
        current_start_idx = 0
        current_chunk_index = 0

        # Zip distances with the *gaps* between sentences.
        # Sentences: S0, S1, S2...
        # Distances: D0 (S0-S1), D1 (S1-S2)...
        # We iterate through distances and pull the *next* sentence (S1, S2...)

        for dist in distances:
            try:
                next_sentence = next(sentences)
            except StopIteration:
                logger.warning("Mismatch: More distances than sentences remaining.")
                break

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

    def _validate_dimensions(self, prev: np.ndarray, current: np.ndarray) -> None:
        if current.shape != prev.shape:
            msg = (
                f"Embedding dimension mismatch: prev {prev.shape}, "
                f"current {current.shape}"
            )
            logger.error(msg)
            raise ValueError(msg)
