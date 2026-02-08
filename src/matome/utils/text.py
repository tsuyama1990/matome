import re
import unicodedata


def normalize_text(text: str) -> str:
    """
    Normalize text using NFKC (Unicode Normalization Form KC).
    This converts full-width alphanumeric characters to half-width, etc.
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
