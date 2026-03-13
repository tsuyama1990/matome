import base64
import os

from cryptography.fernet import Fernet
from pydantic import SecretStr


class SecurityService:
    """Service handling BYOK encryption and description."""

    def __init__(self) -> None:
        key = os.environ.get("ENCRYPTION_KEY", "")
        encoded_key = key.encode("utf-8")
        if len(encoded_key) != 32:
            msg = "Encryption key must be exactly 32 bytes."
            raise ValueError(msg)
        self._fernet = Fernet(base64.urlsafe_b64encode(encoded_key))

    def encrypt_key(self, plain_key: str) -> str:
        """Encrypts an API key."""
        encrypted = self._fernet.encrypt(plain_key.encode("utf-8"))
        return encrypted.decode("utf-8")

    def decrypt_key(self, encrypted_key: str) -> SecretStr:
        """Decrypts an API key back into a SecretStr."""
        decrypted = self._fernet.decrypt(encrypted_key.encode("utf-8"))
        return SecretStr(decrypted.decode("utf-8"))
