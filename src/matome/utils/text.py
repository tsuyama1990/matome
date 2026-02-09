import re
import unicodedata
from collections.abc import Iterator
from functools import lru_cache

# Pre-compile the sentence splitting pattern
# Splits AFTER '。', '！', '？' followed by optional whitespace, OR on one or more newlines.
SENTENCE_SPLIT_PATTERN = re.compile(r"(?<=[。！？])\s*|\n+")


@lru_cache(maxsize=1024)
def normalize_text(text: str) -> str:
    """
    Normalize text using NFKC (Unicode Normalization Form KC).
    This converts full-width alphanumeric characters to half-width, etc.

    Results are cached for performance.
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

        # The sentence is strictly before the separator start?
        # No, because the lookbehind `(?<=X)` matches AFTER X.
        # But wait, `sep_start` is the index where the MATCH starts.
        # If pattern is `(?<=X)`, the match is technically zero-width if nothing follows.
        # But `match.start()` returns the position.
        # If `A。`, match is at 2. `text[0:2]` is `A。`.
        # `sep_start` is 2.

        # If pattern is `\n+`. `A\nB`. Match at 1. `sep_start` is 1.
        # `text[0:1]` is `A`.

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
