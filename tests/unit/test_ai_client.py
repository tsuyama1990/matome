import pytest

from src.domain_models.exceptions import ConfigurationError
from src.infrastructure.ai_client import (
    AIClientConfig,
    AIClientFactory,
    DefaultAICommunicationClient,
)


class DummyHTTPClient:
    def post(self, url, json, headers, timeout, verify=None, auth_token=None):
        return {"choices": [{"message": {"content": "mocked response"}}]}


class DummyRetryPolicy:
    def execute(self, func):
        return func()


class DummyScanner:
    def sanitize(self, text):
        return text


def test_aiclientfactory_invalid_url():
    with pytest.raises(ConfigurationError, match="Invalid API URL configuration: invalid-url"):
        AIClientFactory.create(
            "invalid-url",
            "openai/gpt-4o",
            10,
            DummyHTTPClient(),
            DummyRetryPolicy(),
            DummyScanner(),
        )


def test_aiclientfactory_invalid_timeout():
    with pytest.raises(ConfigurationError, match="Invalid AI timeout value: 0"):
        AIClientFactory.create(
            "https://openrouter.ai/api",
            "openai/gpt-4o",
            0,
            DummyHTTPClient(),
            DummyRetryPolicy(),
            DummyScanner(),
        )


def test_aiclientfactory_invalid_model():
    with pytest.raises(ConfigurationError, match="Invalid default_model configuration"):
        AIClientFactory.create(
            "https://openrouter.ai/api",
            "unverified-model",
            10,
            DummyHTTPClient(),
            DummyRetryPolicy(),
            DummyScanner(),
        )


def test_default_ai_communication_client_unexpected_response_format():
    class BadHTTPClient:
        def post(self, url, json, headers, timeout, verify=None, auth_token=None):
            return {"wrong_key": "data"}

    config = AIClientConfig(api_url="https://test", default_model="openai/gpt-4o", ai_timeout=10)
    client = DefaultAICommunicationClient(
        config, BadHTTPClient(), DummyRetryPolicy(), DummyScanner()
    )

    with pytest.raises(ValueError, match="Unexpected API response format: missing 'choices'."):
        client.call_api("prompt")


def test_default_ai_communication_client_empty_choices():
    class BadHTTPClient:
        def post(self, url, json, headers, timeout, verify=None, auth_token=None):
            return {"choices": []}

    config = AIClientConfig(api_url="https://test", default_model="openai/gpt-4o", ai_timeout=10)
    client = DefaultAICommunicationClient(
        config, BadHTTPClient(), DummyRetryPolicy(), DummyScanner()
    )

    with pytest.raises(
        ValueError, match="Unexpected API response format: 'choices' is empty or invalid."
    ):
        client.call_api("prompt")


def test_default_ai_communication_client_missing_content():
    class BadHTTPClient:
        def post(self, url, json, headers, timeout, verify=None, auth_token=None):
            return {"choices": [{"message": {}}]}

    config = AIClientConfig(api_url="https://test", default_model="openai/gpt-4o", ai_timeout=10)
    client = DefaultAICommunicationClient(
        config, BadHTTPClient(), DummyRetryPolicy(), DummyScanner()
    )

    with pytest.raises(ValueError, match="Unexpected API response format: missing 'content'."):
        client.call_api("prompt")


def test_rotate_credentials():
    class FlushingHTTPClient:
        flushed = False

        def flush_credentials_cache(self):
            self.flushed = True

    client_mock = FlushingHTTPClient()
    config = AIClientConfig(api_url="https://test", default_model="openai/gpt-4o", ai_timeout=10)
    client = DefaultAICommunicationClient(config, client_mock, DummyRetryPolicy(), DummyScanner())
    client.rotate_credentials()
    assert client_mock.flushed


def test_secure_memory_region_stub():
    config = AIClientConfig(api_url="https://test", default_model="openai/gpt-4o", ai_timeout=10)
    client = DefaultAICommunicationClient(
        config, DummyHTTPClient(), DummyRetryPolicy(), DummyScanner()
    )
    # calling it shouldn't crash
    client._secure_memory_region_stub()
