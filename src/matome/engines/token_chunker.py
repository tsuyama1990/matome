import logging
import os
from functools import lru_cache

import tiktoken

from domain_models.config import ProcessingConfig
from domain_models.manifest import Chunk
from matome.utils.text import normalize_text, split_sentences

# Configure logger
logger = logging.getLogger(__name__)

# List of allowed tiktoken model names for security validation
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

        # 1. Normalize
        normalized_text = normalize_text(text)

        # 2. Split into sentences
        sentences = split_sentences(normalized_text)
        logger.debug(f"Split text into {len(sentences)} sentences.")

        # Precompute token counts for performance
        # This avoids repeated calls to self.tokenizer.encode inside the loop if we were doing more complex logic,
        # but even for linear scan, it separates token counting from accumulation logic cleanly.
        sentence_infos = [(s, self.count_tokens(s)) for s in sentences]

        chunks: list[Chunk] = []
        current_chunk_sentences: list[str] = []
        current_tokens = 0
        chunk_index = 0
        start_char_idx = 0

        for sentence, sentence_tokens in sentence_infos:
            if current_tokens + sentence_tokens > config.max_tokens and current_chunk_sentences:
                # Finalize current chunk
                chunk_text = "".join(current_chunk_sentences)
                chunks.append(self._create_chunk(chunk_index, chunk_text, start_char_idx))
                logger.debug(f"Created chunk {chunk_index} with {current_tokens} tokens.")

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
            chunks.append(self._create_chunk(chunk_index, chunk_text, start_char_idx))
            logger.debug(f"Created final chunk {chunk_index} with {current_tokens} tokens.")

        logger.info(f"Successfully split text into {len(chunks)} chunks.")
        return chunks

    def _create_chunk(self, index: int, text: str, start_char_idx: int) -> Chunk:
        """
        Helper method to instantiate a Chunk object.

        Args:
            index: The sequential index of the chunk.
            text: The content of the chunk.
            start_char_idx: The starting character index in the processed stream.

        Returns:
            A populated Chunk model.
        """
        return Chunk(
            index=index,
            text=text,
            start_char_idx=start_char_idx,
            end_char_idx=start_char_idx + len(text),
            metadata={},
        )
