import os

import pytest
from pydantic import SecretStr, ValidationError

from src.config import Settings


def test_settings_api_key_valid() -> None:
    valid_key = "sk-or-v1-validkey12345678901234567890"
    os.environ["OPENROUTER_API_KEY"] = valid_key
    try:
        s = Settings()
        assert s.openrouter_api_key is not None
        assert s.openrouter_api_key.get_secret_value() == valid_key
    finally:
        del os.environ["OPENROUTER_API_KEY"]


def test_settings_api_key_invalid_length() -> None:
    with pytest.raises(ValidationError, match="API Key must be at least 30 characters long"):
        Settings(openrouter_api_key=SecretStr("short"))


def test_settings_api_key_invalid_format() -> None:
    with pytest.raises(ValidationError, match="API Key format is invalid"):
        Settings(
            openrouter_api_key=SecretStr("invalid_key_with_spaces_too_long_to_pass_length_check")
        )
