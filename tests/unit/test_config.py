import os

import pytest
from pydantic import SecretStr, ValidationError

from src.config import Settings


def test_settings_api_key_valid() -> None:
    os.environ["OPENROUTER_API_KEY"] = "sk-or-v1-validkey123"
    s = Settings()
    assert s.openrouter_api_key is not None
    assert s.openrouter_api_key.get_secret_value() == "sk-or-v1-validkey123"
    del os.environ["OPENROUTER_API_KEY"]


def test_settings_api_key_invalid_length() -> None:
    with pytest.raises(ValidationError, match="API Key must be at least 10 characters long"):
        Settings(openrouter_api_key=SecretStr("short"))

def test_settings_api_key_invalid_format() -> None:
    with pytest.raises(ValidationError, match="API Key format is invalid"):
        Settings(openrouter_api_key=SecretStr("invalid key with spaces"))
