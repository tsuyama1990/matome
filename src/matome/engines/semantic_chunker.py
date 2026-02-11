import logging
from collections.abc import Iterable, Iterator

import numpy as np

from domain_models.config import ProcessingConfig
from domain_models.manifest import Chunk
from matome.engines.embedder import EmbeddingService
from matome.utils.compat import batched
from matome.utils.text import iter_normalized_sentences

# Configure logger
logger = logging.getLogger(__name__)


class JapaneseSemanticChunker:
    """
    Chunking engine that splits text based on semantic similarity.
    Supports a "Global Percentile Strategy" for re-iterable inputs (calculating dynamic threshold),
    and a "Static Threshold Strategy" for single-pass streams to ensure memory safety.
    """

    def __init__(self, embedder: EmbeddingService) -> None:
        """
        Initialize with an embedding service.

        Args:
            embedder: Service to generate embeddings for sentences.
        """
        self.embedder = embedder

    def split_text(
        self, text: str | Iterable[str], config: ProcessingConfig
    ) -> Iterator[Chunk]:
        """
        Split text into semantic chunks.

        Args:
            text: Raw input text or iterable of strings (streaming).
            config: Configuration including semantic_chunking_percentile and max_tokens.

        Yields:
            Chunk objects.
        """
        if not text:
            return

        # Helper to get fresh iterator
        def get_sentence_iter() -> Iterator[str]:
            if isinstance(text, str):
                yield from iter_normalized_sentences(text)
            else:
                for item in text:
                    yield from iter_normalized_sentences(item)

        is_reiterable = isinstance(text, (str, list, tuple))
        use_global_strategy = self._should_use_global_strategy(
            text, is_reiterable, config.large_scale_threshold
        )

        if use_global_strategy:
            yield from self._chunk_with_global_percentile(
                get_sentence_iter, config
            )
        else:
            logger.info(
                "Using static threshold strategy for memory safety (input is stream or too large)."
            )
            static_thresh_dist = 1.0 - config.semantic_chunking_threshold
            yield from self._stream_chunk_static(
                get_sentence_iter(), static_thresh_dist, config
            )

    def _should_use_global_strategy(
        self, text: str | Iterable[str], is_reiterable: bool, threshold: int
    ) -> bool:
        """Determine if global strategy should be used based on input type and size."""
        if not is_reiterable:
            return False

        # If it's a huge list of strings, treating it as a stream is safer
        input_len = 0
        if hasattr(text, "__len__"):
            input_len = len(text)  # type: ignore[arg-type]

        if input_len > threshold:
            logger.info(
                f"Input size ({input_len}) exceeds large scale threshold ({threshold}). "
                "Forcing Static Threshold strategy."
            )
            return False

        return True

    def _chunk_with_global_percentile(
        self, get_sentence_iter: Iterable[str], config: ProcessingConfig
    ) -> Iterator[Chunk]:
        """
        Execute chunking using global percentile threshold strategy.
        Requires iterating over sentences twice (once for distances, once for chunking).
        """
        # Pass 1: Calculate Distances
        # Note: get_sentence_iter is a callable returning iterator
        sentences_iter_1 = get_sentence_iter()  # type: ignore[call-arg]
        distances = self._calculate_semantic_distances(sentences_iter_1)

        if not distances:
            # Handle single/empty case
            sentences_iter_single = get_sentence_iter() # type: ignore[call-arg]
            first = next(sentences_iter_single, None)
            if first:
                yield Chunk(
                    index=0, text=first, start_char_idx=0, end_char_idx=len(first)
                )
            return

        # Calc Threshold
        percentile_val = config.semantic_chunking_percentile
        threshold = float(np.percentile(distances, percentile_val))

        logger.info(
            f"Global Semantic Chunking: Calculated threshold {threshold:.4f} at {percentile_val}th percentile."
        )

        # Pass 2: Chunking
        sentences_iter_2 = get_sentence_iter() # type: ignore[call-arg]
        yield from self._create_chunks(
            sentences_iter_2, distances, threshold, config
        )

    def _stream_chunk_static(
        self,
        sentences: Iterator[str],
        threshold_dist: float,
        config: ProcessingConfig,
    ) -> Iterator[Chunk]:
        """
        Chunk sentences using a static threshold in a single pass.
        Uses batched embedding to reduce API calls overhead while maintaining stream.
        """
        try:
            first_sentence = next(sentences)
        except StopIteration:
            return

        current_chunk_sentences: list[str] = [first_sentence]
        current_chunk_len = len(first_sentence)
        current_start_idx = 0
        current_chunk_index = 0

        BATCH_SIZE = config.embedding_batch_size

        # Initial embedding
        # We process the first sentence separately to establish baseline
        first_emb_list = list(self.embedder.embed_strings([first_sentence]))
        if not first_emb_list:
            return
        prev_embedding = np.array(first_emb_list[0])

        # Stream the rest in batches
        for batch in batched(sentences, BATCH_SIZE):
            # batch is tuple of strings
            embeddings = self.embedder.embed_strings(batch)

            # Using strict=True for safety as requested by Ruff
            for sent, emb_list in zip(batch, embeddings, strict=True):
                curr_embedding = np.array(emb_list)

                # Calculate distance
                norm_a = np.linalg.norm(prev_embedding)
                norm_b = np.linalg.norm(curr_embedding)

                if norm_a == 0 or norm_b == 0:
                    sim = 0.0
                else:
                    sim = float(np.dot(prev_embedding, curr_embedding) / (norm_a * norm_b))

                # Clamp and convert to distance
                dist = 1.0 - max(-1.0, min(1.0, sim))

                next_len = len(sent)
                is_semantic_break = dist > threshold_dist
                is_token_overflow = (current_chunk_len + next_len) > config.max_tokens

                if is_semantic_break or is_token_overflow:
                    # Yield current
                    chunk_text = "".join(current_chunk_sentences)
                    yield Chunk(
                        index=current_chunk_index,
                        text=chunk_text,
                        start_char_idx=current_start_idx,
                        end_char_idx=current_start_idx + len(chunk_text),
                        embedding=None,
                    )

                    current_chunk_index += 1
                    current_start_idx += len(chunk_text)
                    current_chunk_sentences = [sent]
                    current_chunk_len = next_len
                else:
                    current_chunk_sentences.append(sent)
                    current_chunk_len += next_len

                prev_embedding = curr_embedding

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

                    # Calculate Cosine Distance
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

    def _validate_dimensions(self, prev: np.ndarray, current: np.ndarray) -> None:
        if current.shape != prev.shape:
            msg = f"Embedding dimension mismatch: prev {prev.shape}, current {current.shape}"
            logger.error(msg)
            raise ValueError(msg)
