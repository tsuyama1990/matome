import os
from unittest import mock

import pytest

from src.config.security import SecurityService
from src.config.settings import AppConfig


def test_encryption_raises_error_on_invalid_key_length() -> None:
    """Test encrypting throws an error if the key is not exactly 32 bytes."""
    with mock.patch.dict(
        os.environ, {"DATABASE_URI": "x", "ENCRYPTION_KEY": "tooshort"}, clear=True
    ):
        config = AppConfig()  # type: ignore[call-arg]

        with pytest.raises(ValueError, match="Encryption key must be exactly 32 bytes."):
            SecurityService(config)
