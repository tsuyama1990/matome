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
    return unicodedata.normalize("NFKC", text)


def iter_sentences(text: str) -> Iterator[str]:
    """
    Lazily yield sentences from text based on Japanese punctuation and newlines.

    This uses `SENTENCE_SPLIT_PATTERN.finditer(text)` to find delimiters,
    and yields the text between them.
    """
    last_idx = 0
    for match in SENTENCE_SPLIT_PATTERN.finditer(text):
        # match.start() is where the separator begins.
        # The sentence is everything before the separator.

        # Note: pattern `(?<=[。！？])` is zero-width lookbehind.
        # It matches AT the position after punctuation.
        # Then `\s*` matches whitespace.
        # If we have `文。`, the lookbehind matches after `。`. `\s*` is empty.
        # match.start() is index after `。`.
        # If we have `文。\n`, `\n+` matches starting at index after `。`.
        # If we have `\n`, it matches at index 0 (if at start).

        # Let's verify standard split logic.
        # If `re.split` works, `finditer` should find the separators.
        # Separator is what `re.split` consumes.
        # Our pattern is `(?<=[。！？])\s*|\n+`.
        # If text is `A。B`, pattern matches at index 2 (after `。`) with length 0 (if no space).
        # finditer will yield a match at (2, 2).
        # chunk before is text[0:2] = "A。"
        # last_idx becomes 2.
        # Next loop starts.

        sep_start = match.start()
        sep_end = match.end()

        # If sep_start == sep_end (zero width match), we must be careful not to infinite loop if we were implementing split manually.
        # But finditer handles moving forward.

        # However, for zero-width lookbehind, the match start is crucial.
        # If `A。B`, match at (2,2).
        # We yield text[0:2].

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
