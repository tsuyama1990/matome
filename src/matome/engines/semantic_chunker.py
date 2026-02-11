import logging
import itertools
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

    def split_text(
        self, text: str | Iterable[str], config: ProcessingConfig
    ) -> Iterator[Chunk]:
        """
        Split text into semantic chunks using global percentile strategy.

        Args:
            text: Raw input text or iterable of strings (streaming).
            config: Configuration including semantic_chunking_percentile and max_tokens.

        Yields:
            Chunk objects.

        Raises:
            ValueError: If input text is not a string or iterable.
        """
        if not text:
            return

        # Helper to get fresh iterator
        def get_sentence_iter() -> Iterator[str]:
            if isinstance(text, str):
                yield from iter_normalized_sentences(text)
            else:
                # If text is an iterable (like a file stream), we can only iterate ONCE unless we use tee.
                # But tee stores data in memory if one branch lags.
                # Semantic chunking requires TWO passes: one for global stats, one for chunking.
                # If streaming from a source we can't rewind, we CANNOT do global percentile optimization
                # without buffering.

                # OPTION 1: Buffer sentences to disk?
                # OPTION 2: Raise error for single-pass stream?
                # OPTION 3: Accept `text` as a RE-ITERABLE (like a list or a file path wrapper),
                # or assume the caller passes a list of strings which is in memory.

                # Given the constraints, if the input is a true single-pass iterator (e.g. generator),
                # we have to load it or we fail pass 2.
                # But we can assume for now that if it's an Iterable, it might be re-iterable (like list)
                # OR we might have to tee it.
                # To be safe for "huge" datasets, user should pass a file path (string) which we stream
                # twice via `iter_sentences`.
                # If they pass a list[str], it's in memory.
                # If they pass a generator, `itertools.tee` is risky for OOM.

                # Compromise: If input is `str`, we re-stream.
                # If input is `Iterable`, we assume it's re-iterable OR we consume it into a temp file?
                # Let's assume for `Iterable` we might just buffer? No, that violates constraints.
                # We will assume `text` as `Iterable` means we iterate chunks.
                # But wait, `split_text` iterates SENTENCES.

                # If the user passes `Iterable[str]` (e.g. lines of a file), we need to iterate it twice.
                # If we can't iterate twice, we can't use global percentile.

                # FIX: We can support `Iterable` ONLY if it allows re-iteration (e.g. list) or if we don't use global percentile?
                # But the algo IS global percentile.

                # Actually, `RaptorEngine` usually passes `text: str`.
                # If we want to support huge docs, we likely pass a file path `str`.
                # `iter_normalized_sentences(path)` could work if we change that utility.
                # But `iter_normalized_sentences` takes `text` content.

                # Let's implement robust handling:
                # If text is str, use iter_normalized_sentences.
                # If text is list, iterate it.
                # If text is iterator, we can't restart.

                # Since `RaptorEngine.run` is the entry point, if it gets a stream, it passes it here.
                # If we MUST support streaming input for semantic chunking, we'd need a local threshold strategy
                # or a temp file buffer.
                # For now, let's assume `Iterable` is passed for batching, and `text` is chunks.
                # But `JapaneseSemanticChunker` works on *sentences*.

                # Let's iterate `text` as items, and normalize each.
                for item in text:
                    yield from iter_normalized_sentences(item)

        # However, we need TWO passes.
        # If `text` is a generator, we are stuck.
        # We will assume `text` is re-iterable (e.g. list or string) OR we use `tee`.
        # Using `tee` on a 10M line file will crash if we consume one branch fully (Pass 1) before touching the other.
        # Yes, `tee` buffers the difference.

        # Pragmatic solution: If `text` is an iterator, warn about memory or require list/str.
        # But we want to support "streaming".
        # If the input is streaming, we can't calculate GLOBAL percentiles without storage.
        # So streaming semantic chunking implies either:
        # 1. Local threshold (not global percentile).
        # 2. Disk buffering.

        # Given the audit "Process text in streaming chunks", `RaptorEngine.run` calling `chunker.split_text`
        # is the bottleneck.
        # If we stick to global percentile, we MUST see all data.
        # Let's implement the `tee` with the assumption that for HUGE datasets, we might fail unless we implement disk buffer.
        # But for this PR, `tee` is better than strict `list()`.
        # Better: Check if `text` is `str` or `list` (re-iterable). If `Iterator`, warn.

        is_reiterable = isinstance(text, (str, list, tuple))

        if is_reiterable:
            # Pass 1
            sentences_iter_1 = get_sentence_iter()
            distances = self._calculate_semantic_distances(sentences_iter_1)

            if not distances:
                # Handle single/empty
                # Need fresh iter
                sentences_iter_single = get_sentence_iter()
                first = next(sentences_iter_single, None)
                if first:
                    yield Chunk(index=0, text=first, start_char_idx=0, end_char_idx=len(first))
                return

            # Calc Threshold
            percentile_val = config.semantic_chunking_percentile
            threshold = float(np.percentile(distances, percentile_val))

            # Pass 2
            sentences_iter_2 = get_sentence_iter()
            yield from self._create_chunks(sentences_iter_2, distances, threshold, config)

        else:
            # Input is likely a generator/iterator.
            # We cannot do 2 passes without buffering.
            # We will use `itertools.tee` but warn.
            # OR we switch to a fixed default threshold if we can't calculate stats?
            # Config has `semantic_chunking_threshold` (default 0.8) which is for "similarity"?
            # Actually config says "Cosine similarity threshold for merging sentences".
            # The code uses `semantic_chunking_percentile` for dynamic threshold.

            # If we are in streaming mode, dynamic threshold is impossible without buffering.
            # Let's use the static `semantic_chunking_threshold` from config if we can't do 2 passes?
            # The class doc says "Global Percentile Strategy".
            # But we can fallback to `config.semantic_chunking_threshold` (similarity) which converts to distance.

            logger.info("Input text is a stream; using static threshold instead of global percentile.")

            # Static threshold logic
            # threshold (distance) = 1.0 - config.semantic_chunking_threshold (similarity)
            static_thresh = 1.0 - config.semantic_chunking_threshold

            # Pass 1? No, we do single pass chunking with static threshold.
            # `_calculate_semantic_distances` consumes stream. We need to chunk AS WE GO.
            # So we need a new method `_stream_chunk_static`.

            yield from self._stream_chunk_static(get_sentence_iter(), static_thresh, config)

    def _stream_chunk_static(
        self,
        sentences: Iterator[str],
        threshold_dist: float,
        config: ProcessingConfig,
    ) -> Iterator[Chunk]:
        """
        Chunk sentences using a static threshold in a single pass.
        """
        try:
            first_sentence = next(sentences)
        except StopIteration:
            return

        current_chunk_sentences: list[str] = [first_sentence]
        current_chunk_len = len(first_sentence)
        current_start_idx = 0
        current_chunk_index = 0

        # We need to embed strictly previous vs current to decide merge.
        # This requires embedding the current sentence to compare with previous.
        # This is expensive (one by one).
        # Optimization: Batch embed a buffer of sentences, process them, then carry over last.

        # Use a buffer to batch embeddings
        BATCH_SIZE = config.embedding_batch_size

        # We need a custom generator that yields (sentence, embedding)
        # But `embed_strings` takes a list/iterable.
        # We can use `batched` on sentences.

        from matome.utils.compat import batched

        # Note: We need to maintain state across batches.
        prev_embedding: np.ndarray | None = None
        # Since we processed `first_sentence` manually, let's embed it first.
        # Or better: treat `first_sentence` as part of the stream but handled specially?

        # Let's restart logic properly.
        # Re-construct stream with first_sentence
        # Actually `sentences` is the iterator. `first_sentence` is already consumed.
        # We'll treat `current_chunk_sentences` as the buffer.

        # Initial embedding
        first_emb_list = list(self.embedder.embed_strings([first_sentence]))
        if not first_emb_list:
            return # Should not happen
        prev_embedding = np.array(first_emb_list[0])

        # Now iterate the rest
        for batch in batched(sentences, BATCH_SIZE):
            # batch is tuple of strings
            embeddings = self.embedder.embed_strings(batch)

            for sent, emb_list in zip(batch, embeddings):
                curr_embedding = np.array(emb_list)

                # Calculate distance
                norm_a = np.linalg.norm(prev_embedding)
                norm_b = np.linalg.norm(curr_embedding)

                if norm_a == 0 or norm_b == 0:
                    sim = 0.0
                else:
                    sim = float(np.dot(prev_embedding, curr_embedding) / (norm_a * norm_b))

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

        # Validation: We expect distances to correspond exactly to gaps.
        # Since we use iterator for sentences, we can't check length upfront.
        # But we consume one distance per next_sentence.

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
