import os
from typing import Any
from unittest import mock

import httpx
import pytest
from cryptography.fernet import Fernet
from pydantic import SecretStr

from src.domain_models.config import ApiCredentials, PipelineConfig
from src.infrastructure.llm_middleware import LLMMiddlewareService
from src.infrastructure.openrouter import OpenRouterGateway
from src.interfaces import LLMError


@pytest.fixture(autouse=True)
def setup_env() -> Any:
    with mock.patch.dict(os.environ, {"MATOME_ENCRYPTION_KEY": "some-random-key"}):
        yield

@pytest.fixture
def valid_config() -> PipelineConfig:
    with mock.patch.dict(os.environ, {"MATOME_ENCRYPTION_KEY": "some-random-key"}):
        config = PipelineConfig(
            credentials=ApiCredentials(openrouter_api_key=SecretStr("sk-or-v1-" + ("A" * 64))),
        )
        from src.infrastructure.crypto import CryptoService
        crypto_service = CryptoService(config.credentials.crypto_config)
        config.credentials.encrypt_key(crypto_service)
        return config



@pytest.fixture
def mock_env_key() -> Any:
    """Fixture to safely inject a valid encryption key for tests."""
    return mock.patch.dict(
        os.environ, {"MATOME_ENCRYPTION_KEY": Fernet.generate_key().decode("utf-8")}
    )


def test_openrouter_gateway_success(valid_config: PipelineConfig, httpx_mock: Any) -> None:
    from src.infrastructure.crypto import CryptoService
    crypto_service = CryptoService(valid_config.credentials.crypto_config)
    gateway = OpenRouterGateway(valid_config.credentials, valid_config, crypto_service)

    httpx_mock.add_response(
        json={"choices": [{"message": {"content": "Mocked LLM response"}}]},
        status_code=200,
    )

    response = gateway.invoke("Test prompt")
    assert response == "Mocked LLM response"


def test_openrouter_gateway_failure(valid_config: PipelineConfig, httpx_mock: Any) -> None:
    from src.infrastructure.crypto import CryptoService
    crypto_service = CryptoService(valid_config.credentials.crypto_config)
    gateway = OpenRouterGateway(valid_config.credentials, valid_config, crypto_service)

    # Note that the gateway retries 3 times, so we need to mock the response for all attempts.
    for _ in range(3):
        httpx_mock.add_response(status_code=500, json={"error": "Internal Server Error"})

    with pytest.raises(LLMError, match="OpenRouter API failed with status 500"):
        gateway.invoke("Test prompt")


def test_openrouter_gateway_timeout(valid_config: PipelineConfig, httpx_mock: Any) -> None:
    from src.infrastructure.crypto import CryptoService
    crypto_service = CryptoService(valid_config.credentials.crypto_config)
    gateway = OpenRouterGateway(valid_config.credentials, valid_config, crypto_service)

    for _ in range(3):
        httpx_mock.add_exception(httpx.TimeoutException("Timeout"))

    with pytest.raises(LLMError, match="Timeout connecting to OpenRouter"):
        gateway.invoke("Test prompt")


def test_openrouter_gateway_invalid_response(valid_config: PipelineConfig, httpx_mock: Any) -> None:
    from src.infrastructure.crypto import CryptoService
    crypto_service = CryptoService(valid_config.credentials.crypto_config)
    gateway = OpenRouterGateway(valid_config.credentials, valid_config, crypto_service)

    for _ in range(3):
        httpx_mock.add_response(json={"invalid_key": "No choices here"}, status_code=200)

    with pytest.raises(LLMError, match="Invalid response format from OpenRouter"):
        gateway.invoke("Test prompt")


def test_openrouter_gateway_request_error(valid_config: PipelineConfig, httpx_mock: Any) -> None:
    from src.infrastructure.crypto import CryptoService
    crypto_service = CryptoService(valid_config.credentials.crypto_config)
    gateway = OpenRouterGateway(valid_config.credentials, valid_config, crypto_service)

    for _ in range(3):
        httpx_mock.add_exception(httpx.RequestError("Network Error"))

    with pytest.raises(LLMError, match="Network error connecting to OpenRouter"):
        gateway.invoke("Test prompt")


def test_openrouter_gateway_missing_content(valid_config: PipelineConfig, httpx_mock: Any) -> None:
    from src.infrastructure.crypto import CryptoService
    crypto_service = CryptoService(valid_config.credentials.crypto_config)
    gateway = OpenRouterGateway(valid_config.credentials, valid_config, crypto_service)

    for _ in range(3):
        httpx_mock.add_response(json={"choices": [{"message": {"other": "value"}}]}, status_code=200)

    with pytest.raises(LLMError, match="Missing content in OpenRouter response"):
        gateway.invoke("Test prompt")


def test_openrouter_gateway_rate_limit(valid_config: PipelineConfig, httpx_mock: Any) -> None:
    valid_config.requests_per_minute_limit = 120  # 0.5s interval
    from src.infrastructure.crypto import CryptoService
    crypto_service = CryptoService(valid_config.credentials.crypto_config)
    gateway = OpenRouterGateway(valid_config.credentials, valid_config, crypto_service)
    middleware = LLMMiddlewareService(gateway, valid_config)

    httpx_mock.add_response(json={"choices": [{"message": {"content": "ok"}}]}, status_code=200)
    httpx_mock.add_response(json={"choices": [{"message": {"content": "ok"}}]}, status_code=200)

    import time

    start = time.time()
    middleware.invoke("Test 1")
    middleware.invoke("Test 2")
    end = time.time()

    assert end - start >= 0.5


def test_openrouter_gateway_rate_limit_zero(valid_config: PipelineConfig, httpx_mock: Any) -> None:
    valid_config.requests_per_minute_limit = 0
    from src.infrastructure.crypto import CryptoService
    crypto_service = CryptoService(valid_config.credentials.crypto_config)
    gateway = OpenRouterGateway(valid_config.credentials, valid_config, crypto_service)
    middleware = LLMMiddlewareService(gateway, valid_config)

    httpx_mock.add_response(json={"choices": [{"message": {"content": "ok"}}]}, status_code=200)

    # Should not sleep or error
    middleware.invoke("Test 1")


def test_openrouter_gateway_network_error(valid_config: PipelineConfig, httpx_mock: Any) -> None:
    from src.infrastructure.crypto import CryptoService
    crypto_service = CryptoService(valid_config.credentials.crypto_config)
    gateway = OpenRouterGateway(valid_config.credentials, valid_config, crypto_service)

    for _ in range(3):
        httpx_mock.add_exception(httpx.RequestError("Network Error"))

    with pytest.raises(LLMError, match="Network error connecting to OpenRouter"):
        gateway.invoke("Test prompt")


def test_openrouter_gateway_sanitize_prompt(valid_config: PipelineConfig, httpx_mock: Any) -> None:
    from src.infrastructure.crypto import CryptoService
    crypto_service = CryptoService(valid_config.credentials.crypto_config)
    gateway = OpenRouterGateway(valid_config.credentials, valid_config, crypto_service)
    middleware = LLMMiddlewareService(gateway, valid_config)

    httpx_mock.add_response(json={"choices": [{"message": {"content": "ok"}}]}, status_code=200)

    # Note the ANSI escape sequence character \x1b which should be stripped
    malicious_prompt = "hello world\x1b[31m"
    middleware.invoke(malicious_prompt)

    request = httpx_mock.get_request()
    import json

    body = json.loads(request.read().decode("utf-8"))

    assert body["messages"][0]["content"] == "hello world[31m"  # control characters removed


def test_openrouter_gateway_missing_key(valid_config: PipelineConfig) -> None:
    """Verifies that missing keys raise an LLMError before attempting to invoke."""
    # Ensure keys are truly empty directly
    valid_config.credentials.openrouter_api_key = None
    valid_config.credentials._encrypted_api_key = None

    from src.infrastructure.crypto import CryptoService
    crypto_service = CryptoService(valid_config.credentials.crypto_config)
    gateway = OpenRouterGateway(valid_config.credentials, valid_config, crypto_service)
    with pytest.raises(LLMError, match="Missing or invalid OpenRouter API key"):
        gateway.invoke("Test prompt")


def test_openrouter_gateway_empty_prompt(valid_config: PipelineConfig) -> None:
    from src.infrastructure.crypto import CryptoService
    crypto_service = CryptoService(valid_config.credentials.crypto_config)
    gateway = OpenRouterGateway(valid_config.credentials, valid_config, crypto_service)
    middleware = LLMMiddlewareService(gateway, valid_config)

    with pytest.raises(ValueError, match="Prompt cannot be empty"):
        middleware.invoke("   ")

    with pytest.raises(ValueError, match="Prompt cannot be empty"):
        middleware.invoke("")


def test_openrouter_gateway_prompt_too_long(valid_config: PipelineConfig) -> None:
    valid_config.max_prompt_length = 5
    from src.infrastructure.crypto import CryptoService
    crypto_service = CryptoService(valid_config.credentials.crypto_config)
    gateway = OpenRouterGateway(valid_config.credentials, valid_config, crypto_service)
    middleware = LLMMiddlewareService(gateway, valid_config)

    with pytest.raises(ValueError, match="Prompt length exceeds maximum allowed length"):
        middleware.invoke("Too long prompt")


def test_openrouter_gateway_schema_validation_error(
    valid_config: PipelineConfig, httpx_mock: Any
) -> None:
    from src.infrastructure.crypto import CryptoService
    crypto_service = CryptoService(valid_config.credentials.crypto_config)
    gateway = OpenRouterGateway(valid_config.credentials, valid_config, crypto_service)

    for _ in range(3):
        httpx_mock.add_response(json={"choices": "not a list"}, status_code=200)

    with pytest.raises(LLMError, match="Invalid response format from OpenRouter"):
        gateway.invoke("Test prompt")
