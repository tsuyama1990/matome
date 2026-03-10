import typing

import pytest

from src.infrastructure.ai_client import (
    AIClientConfig,
    DefaultAICommunicationClient,
)


class DummyHTTPClient:
    def post(
        self,
        url: str,
        json: dict[str, typing.Any],
        headers: dict[str, str],
        timeout: int,
        verify: str | None = None,
        auth_token: typing.Any | None = None,
    ) -> dict[str, typing.Any]:
        return {"choices": [{"message": {"content": "mocked response"}}]}


class DummyRetryPolicy:
    def execute(self, func: typing.Callable[..., typing.Any]) -> typing.Any:
        return func()


class DummyScanner:
    def sanitize(self, text: str | None) -> str:
        return text or ""


def test_default_ai_communication_client_unexpected_response_format() -> None:
    class BadHTTPClient:
        def post(
            self,
            url: str,
            json: dict[str, typing.Any],
            headers: dict[str, str],
            timeout: int,
            verify: str | None = None,
            auth_token: typing.Any | None = None,
        ) -> dict[str, typing.Any]:
            return {"wrong_key": "data"}

    config = AIClientConfig(api_url="https://test", default_model="openai/gpt-4o", ai_timeout=10)
    client = DefaultAICommunicationClient(
        config, BadHTTPClient(), DummyRetryPolicy(), DummyScanner()
    )

    with pytest.raises(ValueError, match="Unexpected API response format: missing 'choices'."):
        client.call_api("prompt")


def test_default_ai_communication_client_empty_choices() -> None:
    class BadHTTPClient:
        def post(
            self,
            url: str,
            json: dict[str, typing.Any],
            headers: dict[str, str],
            timeout: int,
            verify: str | None = None,
            auth_token: typing.Any | None = None,
        ) -> dict[str, typing.Any]:
            return {"choices": []}

    config = AIClientConfig(api_url="https://test", default_model="openai/gpt-4o", ai_timeout=10)
    client = DefaultAICommunicationClient(
        config, BadHTTPClient(), DummyRetryPolicy(), DummyScanner()
    )

    with pytest.raises(
        ValueError, match="Unexpected API response format: 'choices' is empty or invalid."
    ):
        client.call_api("prompt")


def test_default_ai_communication_client_missing_content() -> None:
    class BadHTTPClient:
        def post(
            self,
            url: str,
            json: dict[str, typing.Any],
            headers: dict[str, str],
            timeout: int,
            verify: str | None = None,
            auth_token: typing.Any | None = None,
        ) -> dict[str, typing.Any]:
            return {"choices": [{"message": {}}]}

    config = AIClientConfig(api_url="https://test", default_model="openai/gpt-4o", ai_timeout=10)
    client = DefaultAICommunicationClient(
        config, BadHTTPClient(), DummyRetryPolicy(), DummyScanner()
    )

    with pytest.raises(ValueError, match="Unexpected API response format: missing 'content'."):
        client.call_api("prompt")


def test_rotate_credentials() -> None:
    class FlushingHTTPClient:
        flushed = False

        def flush_credentials_cache(self) -> None:
            self.flushed = True

        def post(
            self,
            url: str,
            json: dict[str, typing.Any],
            headers: dict[str, str],
            timeout: int,
            verify: str | None = None,
            auth_token: typing.Any | None = None,
        ) -> dict[str, typing.Any]:
            return {}

    client_mock = FlushingHTTPClient()
    config = AIClientConfig(api_url="https://test", default_model="openai/gpt-4o", ai_timeout=10)
    client = DefaultAICommunicationClient(config, client_mock, DummyRetryPolicy(), DummyScanner())
    client.rotate_credentials()
    assert client_mock.flushed


def test_secure_memory_region_stub() -> None:
    config = AIClientConfig(api_url="https://test", default_model="openai/gpt-4o", ai_timeout=10)
    client = DefaultAICommunicationClient(
        config, DummyHTTPClient(), DummyRetryPolicy(), DummyScanner()
    )
    # calling it shouldn't crash
    client._secure_memory_region_stub()
