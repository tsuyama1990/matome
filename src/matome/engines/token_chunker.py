import logging
import os
from functools import lru_cache

import tiktoken

from domain_models.config import ProcessingConfig
from domain_models.manifest import Chunk
from matome.utils.text import normalize_text, split_sentences

# Configure logger
logger = logging.getLogger(__name__)

# List of allowed tiktoken model names for security validation.
# We whitelist specific models to prevent arbitrary string injection or unexpected resource usage
# (e.g., loading a model that requires downloading large files or behaving unexpectedly).
ALLOWED_MODELS = {
    "cl100k_base",
    "p50k_base",
    "r50k_base",
    "gpt2",
    "gpt-3.5-turbo",
    "gpt-4",
    "gpt-4o",
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
    # This prevents arbitrary string injection or unexpected model loading
    if model_name not in ALLOWED_MODELS:
        msg = f"Model name '{model_name}' is not in the allowed list."
        logger.error(msg)
        raise ValueError(msg)

    try:
        # tiktoken.get_encoding expects an encoding name (e.g., cl100k_base).
        # However, users often pass model names (e.g., gpt-4).
        # We try encoding_for_model first, then get_encoding.
        try:
            return tiktoken.encoding_for_model(model_name)
        except KeyError:
            # Not a model name, try as encoding name
            return tiktoken.get_encoding(model_name)
    except Exception as e:
        logger.exception(f"Failed to load tokenizer for '{model_name}'")
        msg = f"Could not load tokenizer for '{model_name}'"
        raise ValueError(msg) from e


@lru_cache(maxsize=16)
def _perform_chunking(text: str, max_tokens: int, model_name: str) -> list[Chunk]:
    """
    Core chunking logic, cached for performance.

    Args:
        text: The full text to chunk.
        max_tokens: Maximum tokens per chunk.
        model_name: The tokenizer model name to use.

    Returns:
        A list of Chunk objects.
    """
    # 1. Normalize
    normalized_text = normalize_text(text)

    # 2. Split into sentences
    sentences = split_sentences(normalized_text)

    # Retrieve tokenizer
    tokenizer = get_cached_tokenizer(model_name)

    # Precompute token counts
    sentence_infos = [(s, len(tokenizer.encode(s))) for s in sentences]

    chunks: list[Chunk] = []
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

    for sentence, sentence_tokens in sentence_infos:
        if current_tokens + sentence_tokens > max_tokens and current_chunk_sentences:
            # Finalize current chunk
            chunk_text = "".join(current_chunk_sentences)
            chunks.append(create_chunk(chunk_index, chunk_text, start_char_idx))

            chunk_index += 1
            start_char_idx += len(chunk_text)

            # Reset
            current_chunk_sentences = []
            current_tokens = 0

        current_chunk_sentences.append(sentence)
        current_tokens += sentence_tokens

    # Final chunk
    if current_chunk_sentences:
        chunk_text = "".join(current_chunk_sentences)
        chunks.append(create_chunk(chunk_index, chunk_text, start_char_idx))

    return chunks


class JapaneseTokenChunker:
    """
    Chunking engine optimized for Japanese text.
    Uses regex-based sentence splitting and token-based merging.

    This implements the Chunker protocol.
    """

    def __init__(self, model_name: str | None = None) -> None:
        """
        Initialize the chunker with a specific tokenizer model.

        Args:
            model_name: The name of the encoding to use.
                        Defaults to TIKTOKEN_MODEL_NAME env var or "cl100k_base".
        """
        if model_name is None:
            model_name = os.getenv("TIKTOKEN_MODEL_NAME", "cl100k_base")

        try:
            self.tokenizer = get_cached_tokenizer(model_name)
        except ValueError:
            logger.warning(
                f"Tokenizer loading failed for '{model_name}'. Falling back to 'cl100k_base'."
            )
            # Fallback to cl100k_base
            self.tokenizer = get_cached_tokenizer("cl100k_base")

    def count_tokens(self, text: str) -> int:
        """Count tokens in text."""
        return len(self.tokenizer.encode(text))

    def split_text(self, text: str, config: ProcessingConfig) -> list[Chunk]:
        """
        Split text into chunks.

        Args:
            text: Raw input text.
            config: Configuration including max_tokens.

        Returns:
            List of Chunk objects.
        """
        if not text:
            logger.warning("Empty input text provided to split_text. Returning empty list.")
            return []

        logger.debug(f"Splitting text of length {len(text)} with max_tokens={config.max_tokens}")

        # Delegate to cached function
        # Note: self.tokenizer.name is the encoding name (e.g. "cl100k_base")
        # However, get_cached_tokenizer takes a model name or encoding name.
        # self.tokenizer.name is reliably an encoding name which is in ALLOWED_MODELS if it came from there.
        # But wait, self.tokenizer is a tiktoken.Encoding object. Does it have a 'name' attribute?
        # Yes: encoding.name returns 'cl100k_base' etc.

        chunks = _perform_chunking(text, config.max_tokens, self.tokenizer.name)

        logger.info(f"Successfully split text into {len(chunks)} chunks.")
        return chunks
