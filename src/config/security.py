import base64

from cryptography.fernet import Fernet
from pydantic import SecretStr

from src.config.settings import AppConfig


class SecurityService:
    """Service handling BYOK encryption and description."""

    def __init__(self, config: AppConfig) -> None:
        key = config.encryption_key.get_secret_value()
        self._fernet = Fernet(base64.urlsafe_b64encode(key.encode("utf-8")[:32].ljust(32, b"=")))

    def encrypt_key(self, plain_key: str) -> str:
        """Encrypts an API key."""
        encrypted = self._fernet.encrypt(plain_key.encode("utf-8"))
        return encrypted.decode("utf-8")

    def decrypt_key(self, encrypted_key: str) -> SecretStr:
        """Decrypts an API key back into a SecretStr."""
        decrypted = self._fernet.decrypt(encrypted_key.encode("utf-8"))
        return SecretStr(decrypted.decode("utf-8"))
