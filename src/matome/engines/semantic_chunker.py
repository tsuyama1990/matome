import itertools
import logging
from collections.abc import Iterable, Iterator

import numpy as np

from domain_models.config import ProcessingConfig
from domain_models.manifest import Chunk
from matome.engines.embedder import EmbeddingService
from matome.utils.text import iter_normalized_sentences, iter_normalized_sentences_from_stream

# Configure logger
logger = logging.getLogger(__name__)


class JapaneseSemanticChunker:
    """
    Chunking engine that splits text based on semantic similarity using a Sliding Window Strategy.
    Optimized for memory safety and true streaming (single pass).

    Strategy:
    1. Stream sentences and their embeddings.
    2. Compare current sentence embedding with the previous one.
    3. If similarity drops below threshold (or distance exceeds threshold), split.
    4. Also enforces max_tokens as a hard limit.
    """

    def __init__(self, embedder: EmbeddingService) -> None:
        """
        Initialize with an embedding service.

        Args:
            embedder: Service to generate embeddings for sentences.
        """
        self.embedder = embedder

    def split_text(self, text: str | Iterable[str], config: ProcessingConfig) -> Iterator[Chunk]:
        """
        Split text into semantic chunks using sliding window strategy.
        """
        self._validate_input(text)

        if not text:
            return

        sentences_iter = self._get_sentence_iterator(text)

        # Tee the iterator: one for embedding consumption, one for text access
        # This allows us to stream embeddings while keeping the corresponding text available
        sentences_for_embed, sentences_for_process = itertools.tee(sentences_iter)

        try:
            embeddings_iter = self.embedder.embed_strings(sentences_for_embed)
        except Exception:
            logger.exception("Failed to initiate embedding stream.")
            raise

        dist_threshold = 1.0 - config.semantic_chunking_threshold

        current_sentences: list[str] = []
        current_len = 0
        start_idx = 0
        chunk_index = 0
        prev_embedding: np.ndarray | None = None

        # Process lockstep with strict=True for safety
        for sentence, embedding_list in zip(sentences_for_process, embeddings_iter, strict=True):
            current_embedding = np.array(embedding_list)

            should_split = self._should_split(
                prev_embedding,
                current_embedding,
                dist_threshold,
                current_len,
                len(sentence),
                config.max_tokens
            )

            if should_split and current_sentences:
                chunk, length = self._create_chunk(current_sentences, chunk_index, start_idx)
                yield chunk

                chunk_index += 1
                start_idx += length
                current_sentences = [sentence]
                current_len = len(sentence)
            else:
                current_sentences.append(sentence)
                current_len += len(sentence)

            prev_embedding = current_embedding

        # Final flush
        if current_sentences:
            chunk, _ = self._create_chunk(current_sentences, chunk_index, start_idx)
            yield chunk

    def _get_sentence_iterator(self, text: str | Iterable[str]) -> Iterator[str]:
        if isinstance(text, str):
            return iter_normalized_sentences(text)
        return iter_normalized_sentences_from_stream(text)

    def _should_split(
        self,
        prev_embedding: np.ndarray | None,
        current_embedding: np.ndarray,
        dist_threshold: float,
        current_len: int,
        next_len: int,
        max_tokens: int
    ) -> bool:
        """Determine if a split should occur based on semantic distance or token limit."""
        # 1. Check Hard Token Limit
        if (current_len + next_len) > max_tokens:
            return True

        # 2. Check Semantic Distance
        if prev_embedding is not None:
            self._validate_dimensions(prev_embedding, current_embedding)

            norm_a = np.linalg.norm(prev_embedding)
            norm_b = np.linalg.norm(current_embedding)

            if norm_a == 0 or norm_b == 0:
                sim = 0.0
            else:
                sim = float(np.dot(prev_embedding, current_embedding) / (norm_a * norm_b))

            # Clamp sim and calc distance
            sim = max(-1.0, min(1.0, sim))
            dist = 1.0 - sim

            if dist > dist_threshold:
                return True

        return False

    def _create_chunk(
        self,
        sentences: list[str],
        index: int,
        start_idx: int
    ) -> tuple[Chunk, int]:
        """Create a Chunk object from a list of sentences."""
        chunk_text = "".join(sentences)
        length = len(chunk_text)
        chunk = Chunk(
            index=index,
            text=chunk_text,
            start_char_idx=start_idx,
            end_char_idx=start_idx + length,
            embedding=None,
        )
        return chunk, length

    def _validate_input(self, text: str | Iterable[str]) -> None:
        if not isinstance(text, (str, Iterable)):
            msg = f"Input text must be a string or iterable, got {type(text)}."
            raise TypeError(msg)

    def _validate_dimensions(self, prev: np.ndarray, current: np.ndarray) -> None:
        if current.shape != prev.shape:
            msg = f"Embedding dimension mismatch: prev {prev.shape}, current {current.shape}"
            logger.error(msg)
            raise ValueError(msg)
