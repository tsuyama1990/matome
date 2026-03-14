import pytest

from src.config.security import SecurityService


def test_encryption_raises_error_on_invalid_key_length(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test encrypting throws an error if the key is not exactly 44 bytes."""
    monkeypatch.setenv("ENCRYPTION_KEY", "tooshort")
    with pytest.raises(ValueError, match="Encryption key must be exactly 44 bytes"):
        SecurityService()


def test_encryption_raises_error_on_low_entropy(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test encrypting throws an error if the key has low entropy."""
    monkeypatch.setenv("ENCRYPTION_KEY", "a" * 44)
    with pytest.raises(ValueError, match="Encryption key is too weak"):
        SecurityService()
