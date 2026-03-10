import os

import pytest
from pydantic import SecretStr

from src.config import Settings


def test_settings_api_key_valid(tmp_path: pytest.TempPathFactory) -> None:
    valid_key = "sk-or-v1-validkey12345678901234567890"
    os.environ["OPENROUTER_API_KEY"] = valid_key
    os.environ["TEXT_FAST_MODEL"] = "google/gemini-2.5-flash"
    os.environ["TEXT_REASONING_MODEL"] = "deepseek/deepseek-reasoner"
    os.environ["MULTIMODAL_MODEL"] = "openai/gpt-4o"
    try:
        from src.config import CredentialConfig

        s = Settings(
            credentials=CredentialConfig(
                openrouter_api_key=SecretStr("sk-or-v1-validkey12345678901234567890")
            ),
            openrouter_api_url="https://mock.api.url",
            text_fast_model="google/gemini-2.5-flash",
            text_reasoning_model="deepseek/deepseek-reasoner",
            multimodal_model="openai/gpt-4o",
            allowed_base_dir=str(tmp_path),
        )
        assert s.credentials.openrouter_api_key is not None
        assert s.credentials.openrouter_api_key.get_secret_value() == valid_key
    finally:
        del os.environ["OPENROUTER_API_KEY"]
        del os.environ["TEXT_FAST_MODEL"]
        del os.environ["TEXT_REASONING_MODEL"]
        del os.environ["MULTIMODAL_MODEL"]


def test_settings_api_key_invalid_length(tmp_path: pytest.TempPathFactory) -> None:
    from src.config import CredentialConfig
    from src.domain_models.exceptions import ConfigurationError

    with pytest.raises(ConfigurationError, match="API Key must be at least 30 characters long"):
        Settings(
            credentials=CredentialConfig(openrouter_api_key=SecretStr("short")),
            openrouter_api_url="https://mock.api.url",
            text_fast_model="google/gemini-2.5-flash",
            text_reasoning_model="deepseek/deepseek-reasoner",
            multimodal_model="openai/gpt-4o",
            allowed_base_dir=str(tmp_path),
        )


def test_settings_api_key_invalid_format(tmp_path: pytest.TempPathFactory) -> None:
    from src.config import CredentialConfig
    from src.domain_models.exceptions import ConfigurationError

    with pytest.raises(ConfigurationError, match="API Key format is invalid"):
        Settings(
            credentials=CredentialConfig(
                openrouter_api_key=SecretStr(
                    "invalid_key_with_spaces_too_long_to_pass_length_check"
                )
            ),
            openrouter_api_url="https://mock.api.url",
            text_fast_model="google/gemini-2.5-flash",
            text_reasoning_model="deepseek/deepseek-reasoner",
            multimodal_model="openai/gpt-4o",
            allowed_base_dir=str(tmp_path),
        )
