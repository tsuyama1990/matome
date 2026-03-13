import os
from unittest import mock

import pytest

from src.config.security import SecurityService


def test_encryption_raises_error_on_invalid_key_length() -> None:
    """Test encrypting throws an error if the key is not exactly 32 bytes."""
    with mock.patch.dict(
        os.environ, {"ENCRYPTION_KEY": "tooshort"}, clear=True
    ), pytest.raises(ValueError, match="Encryption key must be exactly 32 bytes."):
        SecurityService()
