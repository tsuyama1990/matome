import base64

import pytest

from src.config.security import SecurityService


def test_encryption_and_decryption_are_reversible(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test encrypting and decrypting a key results in the original plain text."""
    # Setup test config with mock environment variable
    # 44 bytes strictly expected for encryption
    key = base64.urlsafe_b64encode(b"abcdefghijklmnopqrstuvwxyz123456").decode("utf-8")
    monkeypatch.setenv("ENCRYPTION_KEY", key)
    service = SecurityService()

    plain_key = "my-super-secret-api-key"

    encrypted_key = service.encrypt_key(plain_key)
    assert encrypted_key != plain_key

    decrypted_key = service.decrypt_key(encrypted_key)
    assert decrypted_key.get_secret_value() == plain_key


def test_encryption_yields_different_ciphertexts(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test encrypting the same text multiple times gives different ciphertexts (random IVs)."""
    # Using Fernet from cryptography library directly verifies randomized IV creation,
    # as Fernet generates a new IV for each encryption.
    key = base64.urlsafe_b64encode(b"bcdefghijklmnopqrstuvwxyz1234567").decode("utf-8")
    monkeypatch.setenv("ENCRYPTION_KEY", key)
    service = SecurityService()

    plain_key = "some-key"

    encrypted_key_1 = service.encrypt_key(plain_key)
    encrypted_key_2 = service.encrypt_key(plain_key)

    assert encrypted_key_1 != encrypted_key_2

    # Verify both can be decrypted properly
    assert service.decrypt_key(encrypted_key_1).get_secret_value() == plain_key
    assert service.decrypt_key(encrypted_key_2).get_secret_value() == plain_key
