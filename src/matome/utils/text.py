import re
import unicodedata
from collections.abc import Iterator

from domain_models.constants import SENTENCE_SPLIT_PATTERN as SENTENCE_SPLIT_PATTERN_STR

# Pre-compile the sentence splitting pattern
SENTENCE_SPLIT_PATTERN = re.compile(SENTENCE_SPLIT_PATTERN_STR)


def normalize_text(text: str) -> str:
    """
    Normalize text using NFKC (Unicode Normalization Form KC).
    This converts full-width alphanumeric characters to half-width, etc.
    """
    if not text:
        return ""
    return unicodedata.normalize("NFKC", text)


def iter_sentences(text: str) -> Iterator[str]:
    """
    Lazily yield sentences from text based on Japanese punctuation and newlines.

    This uses `SENTENCE_SPLIT_PATTERN.finditer(text)` to find delimiters,
    and yields the text between them.
    """
    if not text:
        return

    last_idx = 0
    for match in SENTENCE_SPLIT_PATTERN.finditer(text):
        sep_start = match.start()
        sep_end = match.end()

        sentence = text[last_idx:sep_start].strip()
        if sentence:
            yield sentence

        last_idx = sep_end

    # Remaining text
    if last_idx < len(text):
        sentence = text[last_idx:].strip()
        if sentence:
            yield sentence


def split_sentences(text: str) -> list[str]:
    """
    Split text into sentences based on Japanese punctuation and newlines.
    """
    return list(iter_sentences(text))


def iter_normalized_sentences(text: str) -> Iterator[str]:
    """
    Lazily yield normalized (NFKC) sentences from raw text.
    This avoids normalizing the entire text at once.
    """
    for sentence in iter_sentences(text):
        yield normalize_text(sentence)
