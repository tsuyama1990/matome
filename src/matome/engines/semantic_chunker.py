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

        Args:
            text: Raw input text or stream of text chunks.
            config: Configuration including semantic_chunking_threshold and max_tokens.

        Yields:
            Chunk objects.

        Raises:
            ValueError: If input text is invalid.
        """
        self._validate_input(text)

        if not text:
            return

        # Prepare sentence iterator
        if isinstance(text, str):
            sentences_iter = iter_normalized_sentences(text)
        else:
            sentences_iter = iter_normalized_sentences_from_stream(text)

        # Tee the iterator: one for embedding consumption, one for text access
        # This allows us to stream embeddings while keeping the corresponding text available
        sentences_for_embed, sentences_for_process = itertools.tee(sentences_iter)

        try:
            embeddings_iter = self.embedder.embed_strings(sentences_for_embed)
        except Exception:
            logger.exception("Failed to initiate embedding stream.")
            raise

        # Similarity threshold (interpret config.semantic_chunking_threshold as similarity)
        # Split if similarity < threshold <=> distance > (1 - threshold)
        # Default 0.8 similarity -> 0.2 distance
        sim_threshold = config.semantic_chunking_threshold
        dist_threshold = 1.0 - sim_threshold

        current_chunk_sentences: list[str] = []
        current_chunk_len = 0
        current_start_idx = 0
        current_chunk_index = 0
        prev_embedding: np.ndarray | None = None

        # Process lockstep
        for sentence, embedding_list in zip(sentences_for_process, embeddings_iter):
            current_embedding = np.array(embedding_list)
            next_len = len(sentence)

            should_split = False

            # Check Semantic Distance
            if prev_embedding is not None:
                self._validate_dimensions(prev_embedding, current_embedding)

                norm_a = np.linalg.norm(prev_embedding)
                norm_b = np.linalg.norm(current_embedding)

                if norm_a == 0 or norm_b == 0:
                    sim = 0.0
                else:
                    sim = float(np.dot(prev_embedding, current_embedding) / (norm_a * norm_b))

                # Clamp sim
                sim = max(-1.0, min(1.0, sim))
                dist = 1.0 - sim

                if dist > dist_threshold:
                    should_split = True

            # Check Hard Token Limit (Character length approximation or strict check if needed)
            # config.max_tokens is roughly chars for Japanese or we trust chunker?
            # Semantic chunker usually uses character length as proxy or needs tokenizer.
            # Here we assume max_tokens acts as character limit if tokenizer not provided,
            # or strictly we should use tokenizer.
            # For simplicity and speed in semantic chunking, we often use char length * factor or just char length.
            # Given JapaneseTokenChunker uses tokenizer, SemanticChunker should ideally too.
            # But adding Tokenizer dependency here might be circular or heavy.
            # We will use simple length check (assuming 1 char ~ 1 token or similar).
            # If strictly required, we should inject tokenizer. For now, strict length check.
            if (current_chunk_len + next_len) > config.max_tokens:
                should_split = True

            if should_split and current_chunk_sentences:
                # Yield current chunk
                chunk_text = "".join(current_chunk_sentences)
                yield Chunk(
                    index=current_chunk_index,
                    text=chunk_text,
                    start_char_idx=current_start_idx,
                    end_char_idx=current_start_idx + len(chunk_text),
                    embedding=None, # Leaf chunks usually don't need stored embedding immediately unless requested
                )

                current_chunk_index += 1
                current_start_idx += len(chunk_text)
                current_chunk_sentences = [sentence]
                current_chunk_len = next_len
            else:
                current_chunk_sentences.append(sentence)
                current_chunk_len += next_len

            prev_embedding = current_embedding

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

    def _validate_input(self, text: str | Iterable[str]) -> None:
        if not isinstance(text, (str, Iterable)):
            msg = f"Input text must be a string or iterable, got {type(text)}."
            raise TypeError(msg)

    def _validate_dimensions(self, prev: np.ndarray, current: np.ndarray) -> None:
        if current.shape != prev.shape:
            msg = f"Embedding dimension mismatch: prev {prev.shape}, current {current.shape}"
            logger.error(msg)
            raise ValueError(msg)
