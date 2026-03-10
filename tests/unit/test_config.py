import os

import pytest


def test_settings_api_key_valid(tmp_path: pytest.TempPathFactory) -> None:
    valid_key = "sk-or-v1-validkey12345678901234567890"
    os.environ["OPENROUTER_API_KEY"] = valid_key
    try:
        from src.config import EnvCredentialProvider

        provider = EnvCredentialProvider()
        with provider.get_api_key() as secure_key:
            assert secure_key._value.decode("utf-8") == valid_key
    finally:
        del os.environ["OPENROUTER_API_KEY"]


def test_settings_api_key_invalid_length(tmp_path: pytest.TempPathFactory) -> None:
    import os

    from src.config import EnvCredentialProvider
    from src.domain_models.exceptions import ConfigurationError

    os.environ["OPENROUTER_API_KEY"] = "short"
    try:
        provider = EnvCredentialProvider()
        with pytest.raises(ConfigurationError, match="API Key must be at least 30 characters long"):
            provider.get_api_key()
    finally:
        del os.environ["OPENROUTER_API_KEY"]


def test_settings_api_key_invalid_format(tmp_path: pytest.TempPathFactory) -> None:
    import os

    from src.config import EnvCredentialProvider
    from src.domain_models.exceptions import ConfigurationError

    os.environ["OPENROUTER_API_KEY"] = "invalid_key_with_spaces_too_long_to_pass_length_check"
    try:
        provider = EnvCredentialProvider()
        with pytest.raises(ConfigurationError, match="API Key format is invalid"):
            provider.get_api_key()
    finally:
        del os.environ["OPENROUTER_API_KEY"]
