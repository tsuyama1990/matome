import logging
from collections.abc import Iterable, Iterator
from functools import lru_cache

import tiktoken

from domain_models.config import ProcessingConfig
from domain_models.constants import ALLOWED_TOKENIZER_MODELS
from domain_models.manifest import Chunk
from matome.utils.text import iter_normalized_sentences

# Configure logger
logger = logging.getLogger(__name__)


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
    if model_name not in ALLOWED_TOKENIZER_MODELS:
        msg = (
            f"Model name '{model_name}' is not in the allowed list. "
            f"Allowed models: {sorted(ALLOWED_TOKENIZER_MODELS)}"
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


def _perform_chunking(
    text: str | Iterable[str], max_tokens: int, model_name: str
) -> Iterator[Chunk]:
    """
    Core chunking logic using streaming.
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

    # Helper to iterate sentences from stream or string
    def sentence_iterator(source: str | Iterable[str]) -> Iterator[str]:
        if isinstance(source, str):
            yield from iter_normalized_sentences(source)
        else:
            for item in source:
                yield from iter_normalized_sentences(item)

    for sentence in sentence_iterator(text):
        sentence_tokens = len(tokenizer.encode(sentence))

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

    This implements the Chunker protocol.
    """

    def __init__(self, config: ProcessingConfig | None = None) -> None:
        """
        Initialize the chunker with a specific tokenizer model.

        Args:
            config: Processing configuration containing tokenizer_model.
        """
        if config is None:
            config = ProcessingConfig()

        # Ensure full Pydantic validation runs even if manually instantiated
        if not isinstance(config, ProcessingConfig):
            config = ProcessingConfig.model_validate(config)

        if config.tokenizer_model not in ALLOWED_TOKENIZER_MODELS:
            msg = (
                f"Tokenizer model '{config.tokenizer_model}' is not allowed. "
                f"Allowed: {sorted(ALLOWED_TOKENIZER_MODELS)}"
            )
            logger.error(msg)
            raise ValueError(msg)

        self.tokenizer = get_cached_tokenizer(config.tokenizer_model)

    def count_tokens(self, text: str) -> int:
        """Count tokens in text."""
        if not text:
            return 0
        return len(self.tokenizer.encode(text))

    def split_text(self, text: str | Iterable[str], config: ProcessingConfig) -> Iterator[Chunk]:
        """
        Split text into chunks (streaming).

        Args:
            text: Raw input text or iterable of text segments.
            config: Configuration including max_tokens and tokenizer_model.

        Yields:
            Chunk objects.
        """
        if not isinstance(text, (str, Iterable)):
            msg = "Input text must be a string or iterable of strings."
            raise TypeError(msg)

        if not text:
            logger.warning("Empty input text provided to split_text. Yielding nothing.")
            return

        chunking_model_name = self.tokenizer.name  # e.g. "cl100k_base"

        # Yield from generator directly
        yield from _perform_chunking(text, config.max_tokens, chunking_model_name)
