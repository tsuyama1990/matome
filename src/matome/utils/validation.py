import base64
import logging
import re
import unicodedata
import urllib.parse
from typing import Any, Final

from domain_models.constants import PROMPT_INJECTION_PATTERNS, SYSTEM_INJECTION_PATTERNS

logger = logging.getLogger(__name__)

# Allow alphanumeric, underscore, hyphen only to prevent injection
VALID_NODE_ID_PATTERN: Final[re.Pattern[str]] = re.compile(r"^[a-zA-Z0-9_\-]+$")


def validate_node_id(node_id: str) -> str:
    """
    Validate node ID format to prevent injection/corruption.

    Args:
        node_id: The ID to validate.

    Returns:
        The validated node ID.

    Raises:
        ValueError: If the ID format is invalid.
    """
    if not VALID_NODE_ID_PATTERN.match(node_id):
        msg = f"Invalid node ID format: {node_id}"
        raise ValueError(msg)
    return node_id


def check_length(text: str, max_input_length: int) -> None:
    """Check document length."""
    if len(text) > max_input_length:
        msg = f"Input text exceeds maximum allowed length ({max_input_length} characters)."
        raise ValueError(msg)


def check_control_chars(text: str, max_input_length: int) -> None:
    """Check for invalid control characters and unicode normalization."""
    # Security: Normalize unicode to prevent homograph/normalization attacks
    normalized_text = unicodedata.normalize("NFKC", text)
    if len(normalized_text) != len(text) and len(normalized_text) > max_input_length:
        msg = "Normalized text exceeds maximum length."
        raise ValueError(msg)

    allowed_controls = {"\n", "\t", "\r"}
    for char in normalized_text:
        if unicodedata.category(char).startswith("C") and char not in allowed_controls:
            msg = f"Input text contains invalid control character: {char!r} (U+{ord(char):04X})"
            raise ValueError(msg)


def check_dos_vectors(text: str, max_word_length: int) -> None:
    """Check for tokenizer DoS vectors (extremely long words)."""
    words = text.split()
    if not words:
        return
    longest_word_len = max((len(w) for w in words), default=0)
    if longest_word_len > max_word_length:
        msg = f"Input text contains extremely long words (>{max_word_length} chars) - potential DoS vector."
        raise ValueError(msg)


def check_injection_patterns(text: str) -> None:
    """Check for prompt and system command injection patterns."""

    # Helper to check a string against patterns
    def check(s: str) -> None:
        # 4. Prompt Injection Check
        for pattern in PROMPT_INJECTION_PATTERNS:
            if re.search(pattern, s, flags=re.IGNORECASE | re.MULTILINE):
                msg = f"Potential prompt injection detected: {pattern}"
                raise ValueError(msg)

        # 5. SQL/System Injection Check
        for pattern in SYSTEM_INJECTION_PATTERNS:
            if re.search(pattern, s, flags=re.IGNORECASE | re.MULTILINE):
                msg = f"Input text contains suspicious pattern (SQL/Command Injection): {pattern}"
                raise ValueError(msg)

    # Check original text
    check(text)

    # Check URL encoded
    try:
        decoded_url = urllib.parse.unquote(text)
        if decoded_url != text:
            check(decoded_url)
    except Exception as e:
        # S110: Log exception
        logger.debug(f"Failed to check URL decoded content: {e}")

    # Check Base64 encoded (heuristic: if it looks like base64, try decoding)
    # We only check if the whole string is base64 or significant chunks?
    # For simplicity, if the text is valid base64, check the decoded content.
    # This is a basic check.
    if len(text) > 10 and len(text) % 4 == 0 and re.match(r"^[A-Za-z0-9+/]+={0,2}$", text):
        try:
            decoded_b64 = base64.b64decode(text, validate=True).decode("utf-8", errors="ignore")
            check(decoded_b64)
        except Exception as e:
            # S110: Log exception
            logger.debug(f"Failed to check Base64 decoded content: {e}")


def sanitize_prompt_injection(text: str, max_input_length: int) -> str:
    """
    Basic mitigation for Prompt Injection.
    Replaces known injection patterns with '[Filtered]'.
    """
    sanitized = text
    for pattern in PROMPT_INJECTION_PATTERNS:
        # Use re.sub with compiled pattern if possible, or just flags
        # Ensure we catch variations
        sanitized = re.sub(pattern, "[Filtered]", sanitized, flags=re.IGNORECASE)

    # Validate length after sanitization just in case replacement significantly increases size
    # (unlikely with [Filtered], but good practice)
    if len(sanitized) > max_input_length:
        msg = "Sanitized text exceeds maximum length."
        raise ValueError(msg)

    return sanitized


def sanitize_instruction(instruction: str, max_length: int) -> str:
    """
    Sanitize user instruction:
    1. Truncate length
    2. Normalize Unicode (NFKC)
    3. Remove non-printable control characters (except newline)
    4. Check for injection patterns
    """
    clean = instruction.strip()

    if len(clean) > max_length:
        clean = clean[:max_length]

    # Normalize
    clean = unicodedata.normalize("NFKC", clean)

    # Remove control characters except standard whitespace
    # Using regex to remove control chars: ranges 00-08, 0B-0C, 0E-1F, 7F
    clean = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', clean)

    check_injection_patterns(clean)

    return clean


def validate_input(text: str, max_input_length: int, max_word_length: int) -> None:
    """
    Sanitize and validate input text.
    Raises ValueError if validation fails.
    """
    check_length(text, max_input_length)
    check_control_chars(text, max_input_length)
    check_dos_vectors(text, max_word_length)
    check_injection_patterns(text)


def validate_context(context: dict[str, Any]) -> None:
    """Recursively validate strings in context dictionary."""
    for key, value in context.items():
        if isinstance(value, str):
            try:
                check_injection_patterns(value)
            except ValueError as e:
                msg = f"Context injection detected in key '{key}': {e}"
                raise ValueError(msg) from e
        elif isinstance(value, dict):
            validate_context(value)
        elif isinstance(value, list):
            for item in value:
                if isinstance(item, str):
                    try:
                        check_injection_patterns(item)
                    except ValueError as e:
                        msg = f"Context injection detected in list item under key '{key}': {e}"
                        raise ValueError(msg) from e
                elif isinstance(item, dict):
                    validate_context(item)
