import os

from cryptography.fernet import Fernet
from pydantic import SecretStr


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

    def decrypt_key(self, encrypted_key: str) -> SecretStr:
        """Decrypts an API key back into a SecretStr."""
        decrypted = self._fernet.decrypt(encrypted_key.encode("utf-8"))
        decoded = decrypted.decode("utf-8")
        if not decoded or len(decoded) < 8:
            msg = "Decrypted key is invalid or too short."
            raise ValueError(msg)
        return SecretStr(decoded)
