import os

import pytest

from src.config import ModeConfig, Settings, create_app_context


def test_settings_default(tmp_path: pytest.TempPathFactory) -> None:
    os.environ["MODE"] = "cli"
    os.environ["TEXT_FAST_MODEL"] = "google/gemini-2.5-flash"
    os.environ["TEXT_REASONING_MODEL"] = "deepseek/deepseek-reasoner"
    os.environ["MULTIMODAL_MODEL"] = "openai/gpt-4o"

    try:
        from pydantic import SecretStr

        settings = Settings(
            openrouter_api_key=SecretStr("sk-or-v1-validkey12345678901234567890"),
            openrouter_api_url="https://mock.api.url",
            text_fast_model="google/gemini-2.5-flash",
            text_reasoning_model="deepseek/deepseek-reasoner",
            multimodal_model="openai/gpt-4o",
            allowed_base_dir=str(tmp_path),
        )
        mode_config = ModeConfig()
        assert mode_config.mode == "cli"
        assert settings.text_fast_model == "google/gemini-2.5-flash"
    finally:
        del os.environ["MODE"]
        del os.environ["TEXT_FAST_MODEL"]
        del os.environ["TEXT_REASONING_MODEL"]
        del os.environ["MULTIMODAL_MODEL"]


def test_app_context_creation(tmp_path: pytest.TempPathFactory) -> None:
    os.environ["MODE"] = "test"
    os.environ["TEXT_FAST_MODEL"] = "google/gemini-2.5-flash"
    os.environ["TEXT_REASONING_MODEL"] = "deepseek/deepseek-reasoner"
    os.environ["MULTIMODAL_MODEL"] = "openai/gpt-4o"

    try:
        from pydantic import SecretStr

        settings = Settings(
            openrouter_api_key=SecretStr("sk-or-v1-validkey12345678901234567890"),
            openrouter_api_url="https://mock.api.url",
            text_fast_model="google/gemini-2.5-flash",
            text_reasoning_model="deepseek/deepseek-reasoner",
            multimodal_model="openai/gpt-4o",
            allowed_base_dir=str(tmp_path),
        )
        mode_config = ModeConfig()
        context = create_app_context(settings, mode_config)
        assert context.mode_config.mode == "test"
        assert context.settings is settings
        assert context.db is None
    finally:
        del os.environ["MODE"]
        del os.environ["TEXT_FAST_MODEL"]
        del os.environ["TEXT_REASONING_MODEL"]
        del os.environ["MULTIMODAL_MODEL"]
