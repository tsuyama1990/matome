import base64
import hashlib
import os

from cryptography.fernet import Fernet
from pydantic import SecretStr

from src.domain_models.config import CryptoConfig


class CryptoService:
    """Service handling cryptographic key derivation and encryption at rest."""

    def __init__(self, config: CryptoConfig) -> None:
        self.config = config
        self._salt = self._derive_salt()
        self._fernet = self._get_fernet_instance()

    def _derive_salt(self) -> bytes:
        # Utilize a secure, environment-injected salt.
        env_salt = os.environ.get("MATOME_SALT")
        if not env_salt:
            msg = "MATOME_SALT environment variable must be securely set to a distinct random string for PBKDF2 operations."
            raise ValueError(msg)
        return env_salt.encode("utf-8")

    def _get_fernet_instance(self) -> Fernet:
        """Derives a secure runtime key using PBKDF2 with a per-process salt."""
        raw_key = os.environ.get("MATOME_ENCRYPTION_KEY")
        if not raw_key:
            msg = "MATOME_ENCRYPTION_KEY environment variable must be set for secure operations."
            raise ValueError(msg)

        derived = hashlib.pbkdf2_hmac(
            self.config.crypto_hash_algorithm,
            raw_key.encode("utf-8"),
            self._salt,
            100000,
            dklen=32,
        )
        return Fernet(base64.urlsafe_b64encode(derived))

    def encrypt(self, secret: SecretStr) -> bytes:
        """Encrypts a SecretStr into raw fernet bytes."""
        return self._fernet.encrypt(secret.get_secret_value().encode("utf-8"))

    def decrypt(self, encrypted_bytes: bytes) -> SecretStr:
        """Decrypts fernet bytes into a securely wrapped Pydantic SecretStr."""
        decrypted_bytes = self._fernet.decrypt(encrypted_bytes)
        return SecretStr(decrypted_bytes.decode("utf-8"))
