import os

import pytest


def test_settings_api_key_valid(tmp_path: pytest.TempPathFactory) -> None:
    valid_key = "sk-or-v1-validkey12345678901234567890"
    try:
        from pydantic import SecretStr
        from src.config import CredentialConfig, EnvCredentialProvider

        config = CredentialConfig(openrouter_api_key=SecretStr(valid_key))
        provider = EnvCredentialProvider(credential_config=config)
        with provider.get_api_key() as secure_key:
            assert secure_key._value.decode("utf-8") == valid_key
    finally:
        pass


def test_settings_api_key_invalid_length(tmp_path: pytest.TempPathFactory) -> None:
    from pydantic import SecretStr
    from src.config import CredentialConfig, EnvCredentialProvider
    from src.domain_models.exceptions import ConfigurationError

    try:
        config = CredentialConfig(openrouter_api_key=SecretStr("short"))
        provider = EnvCredentialProvider(credential_config=config)
        with pytest.raises(ConfigurationError, match="Authentication configuration error."):
            provider.get_api_key()
    finally:
        pass


def test_settings_api_key_invalid_format(tmp_path: pytest.TempPathFactory) -> None:
    from pydantic import SecretStr
    from src.config import CredentialConfig, EnvCredentialProvider
    from src.domain_models.exceptions import ConfigurationError

    try:
        config = CredentialConfig(openrouter_api_key=SecretStr("invalid_key_with_spaces_too_long_to_pass_length_check"))
        provider = EnvCredentialProvider(credential_config=config)
        with pytest.raises(ConfigurationError, match="Authentication configuration error."):
            provider.get_api_key()
    finally:
        pass
