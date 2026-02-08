import tiktoken

from domain_models.config import ProcessingConfig
from domain_models.manifest import Chunk
from matome.utils.text import normalize_text, split_sentences


class JapaneseSemanticChunker:
    """
    Chunking engine optimized for Japanese text.
    Uses regex-based sentence splitting and token-based merging.
    """

    def __init__(self, model_name: str = "cl100k_base") -> None:
        try:
            self.tokenizer = tiktoken.get_encoding(model_name)
        except Exception:
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
        # 1. Normalize
        normalized_text = normalize_text(text)

        # 2. Split into sentences
        sentences = split_sentences(normalized_text)

        chunks: list[Chunk] = []
        current_chunk_sentences: list[str] = []
        current_tokens = 0
        chunk_index = 0
        start_char_idx = 0  # Tracking this is tricky with normalization/re-joining.
        # Ideally we map back to original, but SPEC says "Concatenated chunks == Normalized input" implies we track on normalized.

        # We need to track character index on the normalized text.
        # But split_sentences removes whitespace sometimes or splits on it.
        # For simplicity in Cycle 01, we will construct the chunk text from sentences and approximate indices on the stream of processing.

        # Better approach: Iterate sentences, keep adding to buffer.

        for sentence in sentences:
            sentence_tokens = self.count_tokens(sentence)

            # If a single sentence is too long, we might force split it (Cycle 02),
            # but for now we just add it and it might exceed limit slightly if it's the first one.
            # Or we strictly enforce limit? "Iteratively merge... until limit is reached."

            if current_tokens + sentence_tokens > config.max_tokens and current_chunk_sentences:
                # Finalize current chunk
                chunk_text = "".join(current_chunk_sentences)
                chunks.append(self._create_chunk(chunk_index, chunk_text, start_char_idx))

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
