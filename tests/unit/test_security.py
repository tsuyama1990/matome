import base64
import os
from unittest import mock

from src.config.security import SecurityService
from src.config.settings import AppConfig


def test_encryption_and_decryption_are_reversible() -> None:
    """Test encrypting and decrypting a key results in the original plain text."""
    # Setup test config with mock environment variable
    key = base64.urlsafe_b64encode(os.urandom(32)).decode("utf-8")
    with mock.patch.dict(os.environ, {"DATABASE_URI": "x", "ENCRYPTION_KEY": key}, clear=True):
        config = AppConfig()  # type: ignore[call-arg]
        service = SecurityService(config)

    plain_key = "my-super-secret-api-key"

    encrypted_key = service.encrypt_key(plain_key)
    assert encrypted_key != plain_key

    decrypted_key = service.decrypt_key(encrypted_key)
    assert decrypted_key.get_secret_value() == plain_key


def test_encryption_yields_different_ciphertexts() -> None:
    """Test encrypting the same text multiple times gives different ciphertexts (random IVs)."""
    # Using Fernet from cryptography library directly verifies randomized IV creation,
    # as Fernet generates a new IV for each encryption.
    key = base64.urlsafe_b64encode(os.urandom(32)).decode("utf-8")
    with mock.patch.dict(os.environ, {"DATABASE_URI": "x", "ENCRYPTION_KEY": key}, clear=True):
        config = AppConfig()  # type: ignore[call-arg]
        service = SecurityService(config)

    plain_key = "some-key"

    encrypted_key_1 = service.encrypt_key(plain_key)
    encrypted_key_2 = service.encrypt_key(plain_key)

    assert encrypted_key_1 != encrypted_key_2

    # Verify both can be decrypted properly
    assert service.decrypt_key(encrypted_key_1).get_secret_value() == plain_key
    assert service.decrypt_key(encrypted_key_2).get_secret_value() == plain_key
