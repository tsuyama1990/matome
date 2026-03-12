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


@pytest.fixture
def mock_env_key() -> Any:
    """Fixture to safely inject a valid encryption key for tests."""
    return mock.patch.dict(
        os.environ,
        {
            "MATOME_ENCRYPTION_KEY": Fernet.generate_key().decode("utf-8"),
            "MATOME_SALT": "secure_random_salt_for_testing_12345",
        },
    )


@pytest.fixture
def valid_config(mock_env_key: Any) -> PipelineConfig:
    # mock_env_key must wrap everything doing tests with the decryption phase now!
    with mock_env_key:
        valid_key = "sk-or-v1-" + ("A" * 64)
        config = PipelineConfig()
        config.credentials = ApiCredentials(openrouter_api_key=SecretStr(valid_key))
        return config


@pytest.fixture(autouse=True)
def _auto_mock_env(mock_env_key: Any) -> Any:
    """Ensure MATOME_ENCRYPTION_KEY is available during the request phase in tests."""
    with mock_env_key:
        yield


def test_openrouter_gateway_success(valid_config: PipelineConfig, httpx_mock: Any) -> None:
    gateway = OpenRouterGateway(valid_config.credentials, valid_config)

    httpx_mock.add_response(
        json={"choices": [{"message": {"content": "Mocked LLM response"}}]},
        status_code=200,
    )

    # We need to mock socket.gethostbyname to avoid actual DNS lookup in tests
    with mock.patch("socket.gethostbyname", return_value="8.8.8.8"):
        response = gateway.invoke("Test prompt")
    assert response == "Mocked LLM response"


def test_openrouter_gateway_ssrf_dns_rebinding(
    valid_config: PipelineConfig, httpx_mock: Any
) -> None:
    """Verifies that private/loopback IPs are rejected during DNS resolution."""
    gateway = OpenRouterGateway(valid_config.credentials, valid_config)

    # Mock the DNS resolution to return a loopback IP
    with (
        mock.patch("socket.gethostbyname", return_value="127.0.0.1"),
        pytest.raises(LLMError, match="SSRF Attempt Blocked"),
    ):
        gateway.invoke("Test prompt")


def test_openrouter_gateway_failure(valid_config: PipelineConfig, httpx_mock: Any) -> None:
    gateway = OpenRouterGateway(valid_config.credentials, valid_config)

    # Note that the gateway retries 3 times, so we need to mock the response for all attempts.
    for _ in range(3):
        httpx_mock.add_response(status_code=500, json={"error": "Internal Server Error"})

    with (
        mock.patch("socket.gethostbyname", return_value="8.8.8.8"),
        pytest.raises(LLMError, match="OpenRouter API request failed"),
    ):
        gateway.invoke("Test prompt")


def test_openrouter_gateway_timeout(valid_config: PipelineConfig, httpx_mock: Any) -> None:
    gateway = OpenRouterGateway(valid_config.credentials, valid_config)

    for _ in range(3):
        httpx_mock.add_exception(httpx.TimeoutException("Timeout"))

    with (
        mock.patch("socket.gethostbyname", return_value="8.8.8.8"),
        pytest.raises(LLMError, match="OpenRouter API request failed due to timeout"),
    ):
        gateway.invoke("Test prompt")


def test_openrouter_gateway_invalid_response(valid_config: PipelineConfig, httpx_mock: Any) -> None:
    gateway = OpenRouterGateway(valid_config.credentials, valid_config)

    httpx_mock.add_response(json={"invalid_key": "No choices here"}, status_code=200)

    with (
        mock.patch("socket.gethostbyname", return_value="8.8.8.8"),
        pytest.raises(LLMError, match="Invalid response format from OpenRouter"),
    ):
        gateway.invoke("Test prompt")


def test_openrouter_gateway_request_error(valid_config: PipelineConfig, httpx_mock: Any) -> None:
    gateway = OpenRouterGateway(valid_config.credentials, valid_config)

    for _ in range(3):
        httpx_mock.add_exception(httpx.RequestError("Network Error"))

    with (
        mock.patch("socket.gethostbyname", return_value="8.8.8.8"),
        pytest.raises(LLMError, match="OpenRouter API request failed due to network error"),
    ):
        gateway.invoke("Test prompt")


def test_openrouter_gateway_missing_content(valid_config: PipelineConfig, httpx_mock: Any) -> None:
    gateway = OpenRouterGateway(valid_config.credentials, valid_config)

    httpx_mock.add_response(json={"choices": [{"message": {"other": "value"}}]}, status_code=200)

    with (
        mock.patch("socket.gethostbyname", return_value="8.8.8.8"),
        pytest.raises(LLMError, match="Missing content in OpenRouter response"),
    ):
        gateway.invoke("Test prompt")


def test_openrouter_gateway_rate_limit(valid_config: PipelineConfig, httpx_mock: Any) -> None:
    valid_config.requests_per_minute_limit = 120  # 0.5s interval
    gateway = OpenRouterGateway(valid_config.credentials, valid_config)
    middleware = LLMMiddlewareService(gateway, valid_config)

    httpx_mock.add_response(json={"choices": [{"message": {"content": "ok"}}]}, status_code=200)
    httpx_mock.add_response(json={"choices": [{"message": {"content": "ok"}}]}, status_code=200)

    import time

    with mock.patch("socket.gethostbyname", return_value="8.8.8.8"):
        start = time.time()
        middleware.invoke("Test 1")
        middleware.invoke("Test 2")
        end = time.time()

    assert end - start >= 0.5


def test_openrouter_gateway_rate_limit_zero(valid_config: PipelineConfig, httpx_mock: Any) -> None:
    valid_config.requests_per_minute_limit = 0
    gateway = OpenRouterGateway(valid_config.credentials, valid_config)
    middleware = LLMMiddlewareService(gateway, valid_config)

    httpx_mock.add_response(json={"choices": [{"message": {"content": "ok"}}]}, status_code=200)

    # Should not sleep or error
    with mock.patch("socket.gethostbyname", return_value="8.8.8.8"):
        middleware.invoke("Test 1")


def test_openrouter_gateway_network_error(valid_config: PipelineConfig, httpx_mock: Any) -> None:
    gateway = OpenRouterGateway(valid_config.credentials, valid_config)

    for _ in range(3):
        httpx_mock.add_exception(httpx.RequestError("Network Error"))

    with (
        mock.patch("socket.gethostbyname", return_value="8.8.8.8"),
        pytest.raises(LLMError, match="OpenRouter API request failed due to network error"),
    ):
        gateway.invoke("Test prompt")


def test_openrouter_gateway_sanitize_prompt(valid_config: PipelineConfig, httpx_mock: Any) -> None:
    gateway = OpenRouterGateway(valid_config.credentials, valid_config)
    middleware = LLMMiddlewareService(gateway, valid_config)

    httpx_mock.add_response(json={"choices": [{"message": {"content": "ok"}}]}, status_code=200)

    # Note the ANSI escape sequence character \x1b which should be stripped
    malicious_prompt = "hello world\x1b[31m"
    with mock.patch("socket.gethostbyname", return_value="8.8.8.8"):
        middleware.invoke(malicious_prompt)

    request = httpx_mock.get_request()
    import json

    body = json.loads(request.read().decode("utf-8"))

    assert body["messages"][0]["content"] == "hello world[31m"  # control characters removed


def test_openrouter_gateway_missing_key(valid_config: PipelineConfig) -> None:
    """Verifies that missing keys raise an LLMError before attempting to invoke."""
    # Ensure keys are truly empty directly
    valid_config.credentials.openrouter_api_key = None
    valid_config.credentials.encrypted_key = None
    valid_config.credentials._decrypted_key = None

    gateway = OpenRouterGateway(valid_config.credentials, valid_config)
    with pytest.raises(LLMError, match="Missing or invalid OpenRouter API key"):
        gateway.invoke("Test prompt")


def test_openrouter_gateway_empty_prompt(valid_config: PipelineConfig) -> None:
    gateway = OpenRouterGateway(valid_config.credentials, valid_config)
    middleware = LLMMiddlewareService(gateway, valid_config)

    with pytest.raises(ValueError, match="Prompt cannot be empty"):
        middleware.invoke("   ")

    with pytest.raises(ValueError, match="Prompt cannot be empty"):
        middleware.invoke("")


def test_openrouter_gateway_prompt_too_long(valid_config: PipelineConfig) -> None:
    valid_config.max_prompt_length = 5
    gateway = OpenRouterGateway(valid_config.credentials, valid_config)
    middleware = LLMMiddlewareService(gateway, valid_config)

    with pytest.raises(ValueError, match="Prompt length exceeds maximum allowed length"):
        middleware.invoke("Too long prompt")


def test_openrouter_gateway_schema_validation_error(
    valid_config: PipelineConfig, httpx_mock: Any
) -> None:
    gateway = OpenRouterGateway(valid_config.credentials, valid_config)

    httpx_mock.add_response(json={"choices": "not a list"}, status_code=200)

    with (
        mock.patch("socket.gethostbyname", return_value="8.8.8.8"),
        pytest.raises(LLMError, match="Invalid response format from OpenRouter"),
    ):
        gateway.invoke("Test prompt")
