import logging
from collections.abc import Iterable, Iterator
from typing import Any

import tiktoken
from spacy.language import Language

from domain_models.config import ProcessingConfig
from domain_models.manifest import Chunk
from matome.utils.text import normalize_text

logger = logging.getLogger(__name__)


class TokenChunker:
    """
    Standard Token-based chunker using tiktoken (for OpenAI models).
    """

    def __init__(self) -> None:
        self.encoder = tiktoken.get_encoding("cl100k_base")

    def split_text(self, text: str | Iterable[str], config: ProcessingConfig) -> Iterator[Chunk]:
        """
        Split text into chunks based on token count.
        Supports streaming input.
        """
        max_tokens = config.max_tokens
        overlap = config.overlap

        current_chunk_tokens: list[int] = []
        current_chunk_text_parts: list[str] = []
        current_char_start = 0
        global_char_offset = 0
        chunk_index = 0

        # Create a generator that yields text segments
        input_stream: Iterable[str]
        input_stream = [text] if isinstance(text, str) else text

        for segment in input_stream:
            # Normalize segment
            normalized_segment = normalize_text(segment)
            if not normalized_segment:
                global_char_offset += len(segment)
                continue

            # Tokenize segment
            tokens = self.encoder.encode(normalized_segment)

            token_ptr = 0
            while token_ptr < len(tokens):
                space_left = max_tokens - len(current_chunk_tokens)

                # Take as many tokens as fit
                take_count = min(space_left, len(tokens) - token_ptr)
                tokens_to_take = tokens[token_ptr : token_ptr + take_count]

                current_chunk_tokens.extend(tokens_to_take)

                # Decode to get text part (approximate reconstruction)
                text_part = self.encoder.decode(tokens_to_take)
                current_chunk_text_parts.append(text_part)

                token_ptr += take_count

                if len(current_chunk_tokens) >= max_tokens:
                    # Emit chunk
                    full_text = "".join(current_chunk_text_parts)
                    if full_text.strip():
                        yield Chunk(
                            index=chunk_index,
                            text=full_text,
                            start_char_idx=current_char_start,
                            end_char_idx=current_char_start + len(full_text),
                        )
                        chunk_index += 1

                    # Handle overlap
                    if overlap > 0:
                        overlap_tokens = current_chunk_tokens[-overlap:]
                        current_chunk_tokens = list(overlap_tokens)
                        overlap_text = self.encoder.decode(overlap_tokens)
                        current_chunk_text_parts = [overlap_text]
                        current_char_start += len(full_text) - len(overlap_text)
                    else:
                        current_chunk_tokens = []
                        current_chunk_text_parts = []
                        current_char_start += len(full_text)

        # Emit remaining tokens
        if current_chunk_tokens:
            full_text = "".join(current_chunk_text_parts)
            if full_text.strip():
                yield Chunk(
                    index=chunk_index,
                    text=full_text,
                    start_char_idx=current_char_start,
                    end_char_idx=current_char_start + len(full_text),
                )


class JapaneseTokenChunker:
    """
    Japanese-specific Token Chunker using GiNZA/SpaCy.
    """

    def __init__(self) -> None:
        import spacy
        try:
            self.nlp: Language = spacy.load("ja_ginza")
        except OSError:
            logger.warning("ja_ginza not found, falling back to ja_core_news_sm or blank.")
            try:
                self.nlp = spacy.load("ja_core_news_sm")
            except OSError:
                self.nlp = spacy.blank("ja")

    def count_tokens(self, text: str) -> int:
        """Count tokens in text using the tokenizer."""
        # Simple count for compatibility
        return len(self.nlp(text))

    def _safe_stream(self, text_input: str | Iterable[str]) -> Iterator[str]:
        """
        Yields text segments safe for Sudachi (limit ~49KB bytes, using 10K chars as safe margin).
        Splits large strings in the input stream.
        """
        safe_length = 10000

        # Normalize input to iterable
        raw_stream = [text_input] if isinstance(text_input, str) else text_input

        for segment in raw_stream:
            if len(segment) > safe_length:
                # Split large segment
                for i in range(0, len(segment), safe_length):
                    yield segment[i : i + safe_length]
            else:
                yield segment

    def split_text(self, text: str | Iterable[str], config: ProcessingConfig) -> Iterator[Chunk]:
        """
        Split text into chunks.
        Supports streaming.
        """
        # Use safe stream to avoid Sudachi errors on large inputs
        input_stream = self._safe_stream(text)

        max_tokens = config.max_tokens
        chunk_index = 0

        current_chunk_docs: list[Any] = []
        current_token_count = 0
        current_char_start = 0

        # We process segment by segment using pipe
        # nlp.pipe handles batching internally
        for doc in self.nlp.pipe(input_stream):
            # Iterate sentences in doc
            for sent in doc.sents:
                sent_tokens = len(sent)

                if current_token_count + sent_tokens > max_tokens and current_chunk_docs:
                    # Emit current chunk
                    chunk_text = "".join([s.text for s in current_chunk_docs])
                    yield Chunk(
                        index=chunk_index,
                        text=chunk_text,
                        start_char_idx=current_char_start,
                        end_char_idx=current_char_start + len(chunk_text),
                    )
                    chunk_index += 1

                    # Handle overlap - simplified clear for now
                    current_chunk_docs = []
                    current_token_count = 0
                    current_char_start += len(chunk_text)

                current_chunk_docs.append(sent)
                current_token_count += sent_tokens

        # Emit remaining
        if current_chunk_docs:
            chunk_text = "".join([s.text for s in current_chunk_docs])
            yield Chunk(
                index=chunk_index,
                text=chunk_text,
                start_char_idx=current_char_start,
                end_char_idx=current_char_start + len(chunk_text),
            )
