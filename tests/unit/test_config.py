import os
from unittest import mock

import pytest
from pydantic import ValidationError

from src.config.settings import AppConfig, ModelConfig


def test_app_config_missing_variables() -> None:
    """Test AppConfig raises ValidationError when required env variables are missing."""
    with mock.patch.dict(os.environ, {}, clear=True), pytest.raises(ValidationError):
        AppConfig()  # type: ignore[call-arg]


def test_app_config_success() -> None:
    """Test AppConfig loads correctly when env variables are provided."""
    with mock.patch.dict(
        os.environ,
        {"DATABASE_URI": "test_uri"},
        clear=True,
    ):
        config = AppConfig()  # type: ignore[call-arg]
        assert config.database_uri.get_secret_value() == "test_uri"


def test_model_config_success() -> None:
    """Test ModelConfig loads correctly with env vars."""
    with mock.patch.dict(
        os.environ,
        {
            "OPENROUTER_API_URL": "https://test.openrouter.ai/api",
            "TEXT_FAST_MODEL": "test-model-1",
            "TEXT_REASONING_MODEL": "test-model-2",
            "MULTIMODAL_MODEL": "test-model-3",
            "LLM_TIMEOUT": "45.0",
        },
        clear=True,
    ):
        config = ModelConfig()
        assert str(config.openrouter_api_url) == "https://test.openrouter.ai/api"
        assert config.text_fast_model == "test-model-1"
        assert config.text_reasoning_model == "test-model-2"
        assert config.multimodal_model == "test-model-3"
        assert config.llm_timeout == 45.0
