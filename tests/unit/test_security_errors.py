import os
from unittest import mock

import pytest

from src.config.security import SecurityService


def test_encryption_raises_error_on_invalid_key_length() -> None:
    """Test encrypting throws an error if the key is not exactly 44 bytes."""
    with mock.patch.dict(
        os.environ, {"ENCRYPTION_KEY": "tooshort"}, clear=True
    ), pytest.raises(ValueError, match="Encryption key must be exactly 44 bytes"):
        SecurityService()

def test_encryption_raises_error_on_low_entropy() -> None:
    """Test encrypting throws an error if the key has low entropy."""
    with mock.patch.dict(
        os.environ, {"ENCRYPTION_KEY": "a" * 44}, clear=True
    ), pytest.raises(ValueError, match="Encryption key is too weak"):
        SecurityService()
