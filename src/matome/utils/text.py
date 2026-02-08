import re
import unicodedata
from functools import lru_cache


@lru_cache(maxsize=1024)
def normalize_text(text: str) -> str:
    """
    Normalize text using NFKC (Unicode Normalization Form KC).
    This converts full-width alphanumeric characters to half-width, etc.

    Results are cached for performance.
    """
    return unicodedata.normalize("NFKC", text)


def split_sentences(text: str) -> list[str]:
    """
    Split text into sentences based on Japanese punctuation and newlines.
    Pattern: (?<=[。！？])\\s*|\n+
    This splits AFTER '。', '！', '？' followed by optional whitespace, OR on one or more newlines.
    """
    pattern = r"(?<=[。！？])\s*|\n+"
    sentences = re.split(pattern, text)
    # Remove empty strings resulting from split
    return [s.strip() for s in sentences if s.strip()]
