import logging

import tiktoken

from domain_models.config import ProcessingConfig
from domain_models.manifest import Chunk
from matome.utils.text import normalize_text, split_sentences

# Configure logger
logger = logging.getLogger(__name__)


class JapaneseSemanticChunker:
    """
    Chunking engine optimized for Japanese text.
    Uses regex-based sentence splitting and token-based merging.
    """

    def __init__(self, model_name: str = "cl100k_base") -> None:
        try:
            self.tokenizer = tiktoken.get_encoding(model_name)
        except Exception:
            logger.warning(
                f"Could not load tokenizer '{model_name}', falling back to 'cl100k_base'."
            )
            # Fallback to cl100k_base if model name fails or lookup fails
            self.tokenizer = tiktoken.get_encoding("cl100k_base")

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

        chunks: list[Chunk] = []
        current_chunk_sentences: list[str] = []
        current_tokens = 0
        chunk_index = 0
        start_char_idx = 0

        for sentence in sentences:
            sentence_tokens = self.count_tokens(sentence)

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
        """Helper to create a Chunk object."""
        return Chunk(
            index=index,
            text=text,
            start_char_idx=start_char_idx,
            end_char_idx=start_char_idx + len(text),
            metadata={},
        )
