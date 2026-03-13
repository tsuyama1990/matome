import os
from unittest import mock
from unittest.mock import AsyncMock, patch

import httpx
import pytest

from src.config.settings import ModelConfig
from src.infrastructure.llm_gateway import LLMError, OpenRouterGateway


@pytest.mark.asyncio
async def test_llm_gateway_success() -> None:
    config = ModelConfig(
        openrouter_api_url="https://test.com/api",
        text_fast_model="test-model",
        text_reasoning_model="test-model",
        multimodal_model="test-model"
    )
    with patch.dict(os.environ, {"OPENROUTER_API_KEY": "valid_test_api_key_longer_than_10_chars"}, clear=True):
        gateway = OpenRouterGateway(config)
        with patch.object(gateway._client, 'post', new_callable=AsyncMock) as mock_post:
            mock_post.return_value.raise_for_status = mock.MagicMock()
            mock_post.return_value.json = mock.MagicMock(return_value={
                "choices": [{"message": {"content": "Hello World"}}]
            })
            result = await gateway.generate("test prompt")
            assert result == "Hello World"
        await gateway.close()

@pytest.mark.asyncio
async def test_llm_gateway_missing_api_key() -> None:
    config = ModelConfig()
    with patch.dict(os.environ, {}, clear=True):
        gateway = OpenRouterGateway(config)
        with pytest.raises(ValueError, match="OPENROUTER_API_KEY environment variable is missing"):
            await gateway.generate("test prompt")
        await gateway.close()

@pytest.mark.asyncio
async def test_llm_gateway_http_error() -> None:
    config = ModelConfig()
    with patch.dict(os.environ, {"OPENROUTER_API_KEY": "valid_test_api_key_longer_than_10_chars"}, clear=True):
        gateway = OpenRouterGateway(config)
        with patch.object(gateway._client, 'post', new_callable=AsyncMock) as mock_post:
            mock_post.return_value.raise_for_status = mock.MagicMock(side_effect=httpx.HTTPStatusError(
                "error", request=httpx.Request("POST", "url"), response=httpx.Response(400)
            ))
            with pytest.raises(LLMError, match="LLM API request failed due to an HTTP error."):
                await gateway.generate("test prompt")
        await gateway.close()

@pytest.mark.asyncio
async def test_llm_gateway_request_error() -> None:
    config = ModelConfig()
    with patch.dict(os.environ, {"OPENROUTER_API_KEY": "valid_test_api_key_longer_than_10_chars"}, clear=True):
        gateway = OpenRouterGateway(config)
        with patch.object(gateway._client, 'post', new_callable=AsyncMock) as mock_post:
            mock_post.side_effect = httpx.RequestError("error", request=httpx.Request("POST", "url"))
            with pytest.raises(LLMError, match="LLM API request failed due to a network error."):
                await gateway.generate("test prompt")
        await gateway.close()
