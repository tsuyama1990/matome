import logging
import os
from collections.abc import Iterable, Iterator
from functools import lru_cache
from typing import TYPE_CHECKING

import numpy as np
import tiktoken

from domain_models.config import ProcessingConfig
from domain_models.manifest import Chunk
from matome.utils.text import SENTENCE_SPLIT_PATTERN, normalize_text

if TYPE_CHECKING:
    from matome.engines.embedder import EmbeddingService

# Configure logger
logger = logging.getLogger(__name__)

# List of allowed tiktoken model names for security validation.
# Only tokenization/embedding models are allowed. LLM models (e.g., gpt-4) are excluded.
# To add a new model, ensure it is a tokenizer or embedding model and not a generative model endpoint.
ALLOWED_MODELS = {
    "cl100k_base",
    "p50k_base",
    "r50k_base",
    "text-embedding-ada-002",
    "text-embedding-3-small",
    "text-embedding-3-large",
}


@lru_cache(maxsize=4)
def get_cached_tokenizer(model_name: str) -> tiktoken.Encoding:
    """
    Get a cached tokenizer instance.

    Args:
        model_name: The name of the encoding/model to load.

    Returns:
        The tiktoken Encoding object.

    Raises:
        ValueError: If the model name is not allowed or invalid.
    """
    # Security check: Validate input model name against allowed list
    if model_name not in ALLOWED_MODELS:
        msg = (
            f"Model name '{model_name}' is not in the allowed list. "
            f"Allowed models: {sorted(ALLOWED_MODELS)}"
        )
        logger.error(msg)
        raise ValueError(msg)

    try:
        try:
            return tiktoken.encoding_for_model(model_name)
        except KeyError:
            return tiktoken.get_encoding(model_name)
    except Exception as e:
        logger.exception(f"Failed to load tokenizer for '{model_name}'")
        msg = f"Could not load tokenizer for '{model_name}'. Check internet connection or model name validity."
        raise ValueError(msg) from e


def _extract_sentences(buffer: str, is_final: bool) -> tuple[list[str], int]:
    """
    Helper to extract complete sentences from buffer.
    Returns a list of sentences and the index where processing stopped.
    """
    sentences = []
    last_idx = 0
    matches = list(SENTENCE_SPLIT_PATTERN.finditer(buffer))

    for match in matches:
        sep_start = match.start()
        sep_end = match.end()

        # If not final, avoid splitting at the very end (incomplete separator)
        if not is_final and sep_end == len(buffer):
            break

        sentence = buffer[last_idx:sep_start].strip()
        if sentence:
            sentences.append(sentence)
        last_idx = sep_end

    return sentences, last_idx


def _iter_sentences_from_stream(text_iter: Iterable[str]) -> Iterator[str]:
    """
    Yield sentences from a stream of text chunks.
    Handles buffering to ensure regex splitting works across chunk boundaries.
    """
    buffer = ""

    for block in text_iter:
        if not block:
            continue

        buffer += normalize_text(block)

        sentences, processed_idx = _extract_sentences(buffer, is_final=False)
        yield from sentences

        if processed_idx > 0:
            buffer = buffer[processed_idx:]

    # Process remaining buffer
    if buffer:
        sentences, processed_idx = _extract_sentences(buffer, is_final=True)
        yield from sentences

        # Remaining text after last separator
        if processed_idx < len(buffer):
            remaining = buffer[processed_idx:].strip()
            if remaining:
                yield remaining


def _perform_chunking(text_iter: Iterable[str], max_tokens: int, model_name: str) -> Iterator[Chunk]:
    """
    Core chunking logic with streaming support.
    """
    # Retrieve tokenizer
    tokenizer = get_cached_tokenizer(model_name)

    current_chunk_sentences: list[str] = []
    current_tokens = 0
    chunk_index = 0
    start_char_idx = 0

    def create_chunk(idx: int, content: str, start: int) -> Chunk:
        return Chunk(
            index=idx,
            text=content,
            start_char_idx=start,
            end_char_idx=start + len(content),
            metadata={},
        )

    # Use iterator for sentences from stream
    for sentence in _iter_sentences_from_stream(text_iter):
        sentence_tokens = len(tokenizer.encode(sentence))

        # Check if adding this sentence exceeds the limit
        if current_tokens + sentence_tokens > max_tokens and current_chunk_sentences:
            chunk_text = "".join(current_chunk_sentences)
            yield create_chunk(chunk_index, chunk_text, start_char_idx)

            chunk_index += 1
            start_char_idx += len(chunk_text)

            current_chunk_sentences = []
            current_tokens = 0

        current_chunk_sentences.append(sentence)
        current_tokens += sentence_tokens

    # Final chunk
    if current_chunk_sentences:
        chunk_text = "".join(current_chunk_sentences)
        yield create_chunk(chunk_index, chunk_text, start_char_idx)


class JapaneseTokenChunker:
    """
    Chunking engine optimized for Japanese text.
    Uses regex-based sentence splitting and token-based merging.
    Supports streaming input.

    This implements the Chunker protocol.
    """

    def __init__(self, model_name: str | None = None) -> None:
        """
        Initialize the chunker.

        Args:
            model_name: Optional default model name for count_tokens.
                        If not provided, falls back to env var or cl100k_base.
                        Validates the model name against allowed list.
        """
        # If model_name is passed or read from env, it MUST be validated
        self.default_model_name = model_name or os.getenv("TIKTOKEN_MODEL_NAME") or "cl100k_base"

        # Validate immediately
        # get_cached_tokenizer performs the check against ALLOWED_MODELS
        # This prevents starting with an unsafe configuration
        try:
            get_cached_tokenizer(self.default_model_name)
        except ValueError:
            logger.exception(f"Invalid default model configuration: {self.default_model_name}")
            raise

    def count_tokens(self, text: str, model_name: str | None = None) -> int:
        """Count tokens in text."""
        if not text:
            return 0
        model = model_name or self.default_model_name
        tokenizer = get_cached_tokenizer(model)
        return len(tokenizer.encode(text))

    def split_text(self, text: str | Iterable[str], config: ProcessingConfig) -> Iterator[Chunk]:
        """
        Split text into chunks.

        Args:
            text: Raw input text (str) or iterable of text segments.
            config: Configuration including chunking settings.

        Returns:
            Iterator of Chunk objects.
        """
        if text is None:
            return

        # Check for emptiness only if it's falsy (empty str or empty list)
        # If generator, we can't know without consuming.
        if not text and isinstance(text, (str, list)):
             return

        # Use model from config
        model_name = config.chunking.tokenizer_model

        # If text is string, wrap in list for uniform processing
        if isinstance(text, str):
             text_iter: Iterable[str] = [text]
        else:
             text_iter = text

        logger.debug(f"Splitting text with max_tokens={config.chunking.max_tokens}, model={model_name}")

        yield from _perform_chunking(text_iter, config.chunking.max_tokens, model_name)


class JapaneseSemanticChunker:
    """
    Semantic chunker for Japanese text.
    Uses embeddings to merge sentences based on semantic similarity.
    """

    def __init__(self, embedder: "EmbeddingService") -> None:
        """
        Initialize the semantic chunker.

        Args:
            embedder: An instance of EmbeddingService to generate sentence embeddings.
        """
        self.embedder = embedder

    def split_text(self, text: str | Iterable[str], config: ProcessingConfig) -> Iterator[Chunk]:
        """
        Split text into chunks based on semantic similarity.

        Args:
            text: Input text or iterable of text segments.
            config: Configuration including semantic chunking parameters.

        Returns:
            Iterator of Chunk objects.
        """
        # 1. Collect sentences
        if isinstance(text, str):
            text_iter: Iterable[str] = [text]
        else:
            text_iter = text

        # We need to consume the stream to perform global semantic analysis (or windowed).
        # For simplicity in this iteration, we process the whole document.
        sentences = list(_iter_sentences_from_stream(text_iter))
        if not sentences:
            return

        # 2. Embed sentences
        try:
            # self.embedder.embed_strings returns list[list[float]]
            embeddings = self.embedder.embed_strings(sentences)
        except Exception:
            logger.exception("Failed to embed sentences for semantic chunking.")
            return

        if not embeddings:
            return

        # 3. Calculate similarities
        embeddings_np = np.array(embeddings)
        n_sentences = len(sentences)

        if n_sentences < 2:
            yield Chunk(
                index=0,
                text=sentences[0],
                start_char_idx=0,
                end_char_idx=len(sentences[0]),
                embedding=embeddings[0]
            )
            return

        # Calculate cosine similarity between adjacent sentences
        # Output shape: (n_sentences-1, )
        # Normalize for cosine similarity
        norms = np.linalg.norm(embeddings_np, axis=1, keepdims=True)
        norms[norms == 0] = 1e-10  # Avoid division by zero
        normalized = embeddings_np / norms

        # Adjacent similarity: dot product of i and i+1
        similarities = np.sum(normalized[:-1] * normalized[1:], axis=1)

        # Calculate distances (dissimilarity)
        distances = 1 - similarities

        # 4. Determine threshold
        mode = config.chunking.semantic_chunking_mode
        if mode == "percentile":
            threshold = np.percentile(distances, config.chunking.semantic_chunking_percentile)
        else:
            # Fixed threshold for similarity means we split if sim < threshold
            # Equivalent to distance > (1 - threshold)
            threshold = 1 - config.chunking.semantic_chunking_threshold

        # 5. Merge based on threshold
        current_chunk_sentences: list[str] = [sentences[0]]
        current_chunk_embeddings: list[list[float]] = [embeddings[0]]
        current_start_idx = 0
        chunk_idx = 0

        for i, dist in enumerate(distances):
            # dist is distance between sentence[i] and sentence[i+1]
            if dist > threshold:
                # Split point found
                chunk_text = "".join(current_chunk_sentences)

                # Compute centroid embedding for the chunk
                chunk_embedding = np.mean(current_chunk_embeddings, axis=0).tolist()

                yield Chunk(
                    index=chunk_idx,
                    text=chunk_text,
                    start_char_idx=current_start_idx,
                    end_char_idx=current_start_idx + len(chunk_text),
                    embedding=chunk_embedding
                )

                chunk_idx += 1
                current_start_idx += len(chunk_text)
                current_chunk_sentences = [sentences[i+1]]
                current_chunk_embeddings = [embeddings[i+1]]
            else:
                # Merge
                current_chunk_sentences.append(sentences[i+1])
                current_chunk_embeddings.append(embeddings[i+1])

        # Final chunk
        if current_chunk_sentences:
            chunk_text = "".join(current_chunk_sentences)
            chunk_embedding = np.mean(current_chunk_embeddings, axis=0).tolist()
            yield Chunk(
                index=chunk_idx,
                text=chunk_text,
                start_char_idx=current_start_idx,
                end_char_idx=current_start_idx + len(chunk_text),
                embedding=chunk_embedding
            )
