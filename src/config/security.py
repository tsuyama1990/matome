import os
import re

import bleach
from cryptography.fernet import Fernet
from pydantic import SecretStr


class DecryptionError(Exception):
    """Custom exception raised when BYOK decryption fails."""


class SecurityService:
    """Service handling BYOK encryption and description."""

    def __init__(self) -> None:
        key = os.environ.get("ENCRYPTION_KEY")
        if not key:
            msg = "ENCRYPTION_KEY environment variable is missing."
            raise ValueError(msg)

        encoded_key = key.encode("utf-8")
        if len(encoded_key) != 44:
            msg = "Encryption key must be exactly 44 bytes (32-byte url-safe base64-encoded)."
            raise ValueError(msg)

        # Entropy check: Ensure it's not just a single repeated character
        if len(set(encoded_key)) < 16:
            msg = "Encryption key is too weak (low entropy)."
            raise ValueError(msg)

        self._fernet = Fernet(encoded_key)

    def encrypt_key(self, plain_key: str) -> str:
        """Encrypts an API key."""
        encrypted = self._fernet.encrypt(plain_key.encode("utf-8"))
        return encrypted.decode("utf-8")

    import contextlib
    from collections.abc import Generator

    def _validate_decoded_key(self, decoded: str) -> None:
        if not decoded or len(decoded) < 8:
            msg = "Decrypted key is invalid or too short."
            raise ValueError(msg)

    @contextlib.contextmanager
    def get_decrypted_key(self, encrypted_key: str) -> Generator[str, None, None]:
        """Decrypts an API key and yields it securely, ensuring memory is cleared."""
        try:
            decrypted = self._fernet.decrypt(encrypted_key.encode("utf-8"))
            decoded = decrypted.decode("utf-8")
            self._validate_decoded_key(decoded)
        except Exception as e:
            msg = "Failed to decrypt key"
            raise DecryptionError(msg) from e

        try:
            yield decoded
        finally:
            # Although Python GC is not deterministic, we clear the reference explicitly
            decoded = "0" * len(decoded)
            decrypted = b"0" * len(decrypted)
            del decoded
            del decrypted

    def decrypt_key(self, encrypted_key: str) -> SecretStr:
        """Decrypts an API key back into a SecretStr."""
        with self.get_decrypted_key(encrypted_key) as decoded:
            return SecretStr(decoded)

def sanitize_text(content: str) -> str:
    """
    Comprehensive sanitization of user-provided content.
    Prevents XSS via Bleach and filters hazardous control characters.
    """


    # Reject all ASCII control characters except tab, newline, and carriage return
    # \x00-\x08 (0-8), \x0B (11), \x0C (12 form feed), \x0E-\x1F (14-31), \x7F (127 DEL)
    if re.search(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]", content):
        msg = "Content contains forbidden control characters."
        raise ValueError(msg)

    # Use bleach to completely strip all HTML elements, attributes, and protocols
    sanitized_content = bleach.clean(
        content,
        tags=[],
        attributes={},
        protocols=[],
        strip=True
    )

    if not sanitized_content.strip():
        msg = "Content is empty after sanitization."
        raise ValueError(msg)

    return sanitized_content
