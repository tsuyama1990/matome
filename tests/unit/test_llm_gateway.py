import httpx
import pytest

from src.config.settings import ModelConfig
from src.infrastructure.llm_gateway import LLMError, OpenRouterGateway
from src.infrastructure.test_services import SafeTestHTTPTransport


def setup_encryption_env(
    monkeypatch: pytest.MonkeyPatch,
    key: str = "sk-or-v1-abcdef0123456789abcdef0123456789abcdef0123456789abcdef0123456789",
) -> None:
    """Helper to setup encrypted API key and encryption key."""
    from src.config.security import SecurityService

    encryption_key = "abcdefghijklmnopqrstuvwxyz12345678901234567="
    monkeypatch.setenv("ENCRYPTION_KEY", encryption_key)
    service = SecurityService()
    encrypted_api_key = service.encrypt_key(key)
    monkeypatch.setenv("OPENROUTER_API_KEY_ENCRYPTED", encrypted_api_key)


@pytest.mark.asyncio
async def test_llm_gateway_success(monkeypatch: pytest.MonkeyPatch) -> None:
    from pydantic import AnyHttpUrl

    # Since the tests do not mock getaddrinfo anymore due to anti-mocking rules,
    # we need to use a domain that resolves natively, such as example.com
    config = ModelConfig(
        openrouter_api_url=AnyHttpUrl("https://example.com/api"),
        text_fast_model="test-model",
        text_reasoning_model="test-model",
        multimodal_model="test-model",
        allowed_hosts=["example.com"],
    )
    setup_encryption_env(monkeypatch)

    async with OpenRouterGateway(config) as gateway:
        test_transport = SafeTestHTTPTransport(
            response_data={"choices": [{"message": {"content": "Hello World"}}]}
        )
        gateway._client = httpx.AsyncClient(transport=test_transport)

        result = await gateway.generate("test prompt")
        assert result == "Hello World"


@pytest.mark.asyncio
async def test_llm_gateway_missing_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    from pydantic import AnyHttpUrl

    monkeypatch.setenv("ENCRYPTION_KEY", "abcdefghijklmnopqrstuvwxyz12345678901234567=")
    monkeypatch.delenv("OPENROUTER_API_KEY_ENCRYPTED", raising=False)

    # Validation logic will fail early, but config can be valid structurally
    config = ModelConfig(
        openrouter_api_url=AnyHttpUrl("https://example.com/api"),
        text_fast_model="test-model",
        text_reasoning_model="test-model",
        multimodal_model="test-model",
        allowed_hosts=["example.com"],
    )
    with pytest.raises(
        ValueError, match="OPENROUTER_API_KEY_ENCRYPTED environment variable is missing or empty."
    ):
        OpenRouterGateway(config)


@pytest.mark.asyncio
async def test_llm_gateway_invalid_api_key_format(monkeypatch: pytest.MonkeyPatch) -> None:
    from pydantic import AnyHttpUrl

    config = ModelConfig(
        openrouter_api_url=AnyHttpUrl("https://example.com/api"),
        text_fast_model="test-model",
        text_reasoning_model="test-model",
        multimodal_model="test-model",
        allowed_hosts=["example.com"],
    )
    setup_encryption_env(monkeypatch, key="invalid-format-key")
    async with OpenRouterGateway(config) as gateway:
        with pytest.raises(
            ValueError, match="Decrypted API key does not match expected OpenRouter format."
        ):
            await gateway.generate("test prompt")


@pytest.mark.asyncio
async def test_llm_gateway_http_error(monkeypatch: pytest.MonkeyPatch) -> None:
    from pydantic import AnyHttpUrl

    config = ModelConfig(
        openrouter_api_url=AnyHttpUrl("https://example.com/api"),
        text_fast_model="test-model",
        text_reasoning_model="test-model",
        multimodal_model="test-model",
        allowed_hosts=["example.com"],
    )
    setup_encryption_env(monkeypatch)

    async with OpenRouterGateway(config) as gateway:
        test_transport = SafeTestHTTPTransport(response_data={}, status_code=400)
        gateway._client = httpx.AsyncClient(transport=test_transport)

        with pytest.raises(LLMError, match="LLM API request failed due to an HTTP error: 400."):
            await gateway.generate("test prompt")


@pytest.mark.asyncio
async def test_llm_gateway_request_error(monkeypatch: pytest.MonkeyPatch) -> None:
    from pydantic import AnyHttpUrl

    config = ModelConfig(
        openrouter_api_url=AnyHttpUrl("https://example.com/api"),
        text_fast_model="test-model",
        text_reasoning_model="test-model",
        multimodal_model="test-model",
        allowed_hosts=["example.com"],
    )
    setup_encryption_env(monkeypatch)

    async with OpenRouterGateway(config) as gateway:
        req = httpx.Request("POST", "https://example.com/url")
        test_transport = SafeTestHTTPTransport(
            response_data={}, raise_exception=httpx.RequestError("error", request=req)
        )
        gateway._client = httpx.AsyncClient(transport=test_transport)

        with pytest.raises(
            LLMError, match="LLM API request failed due to a network error after retries."
        ):
            await gateway.generate("test prompt")


@pytest.mark.asyncio
async def test_ssrf_dns_fail(monkeypatch: pytest.MonkeyPatch) -> None:
    import socket

    from httpcore._backends.anyio import AnyIOBackend

    from src.infrastructure.network import SSRFProtectedBackend

    def mock_getaddrinfo(*args: object, **kwargs: object) -> list[object]:
        msg = "dns failed"
        raise socket.gaierror(msg)

    monkeypatch.setattr(socket, "getaddrinfo", mock_getaddrinfo)
    backend = SSRFProtectedBackend(AnyIOBackend(), allowed_hosts=["openrouter.ai"])
    with pytest.raises(ValueError, match="DNS resolution failed"):
        await backend.connect_tcp("openrouter.ai", 80)


@pytest.mark.asyncio
async def test_ssrf_disallowed_host() -> None:
    from httpcore._backends.anyio import AnyIOBackend

    from src.infrastructure.network import SSRFProtectedBackend

    backend = SSRFProtectedBackend(AnyIOBackend(), allowed_hosts=["openrouter.ai"])
    with pytest.raises(ValueError, match="is not in the allowed list"):
        await backend.connect_tcp("malicious.com", 80)


@pytest.mark.asyncio
async def test_ssrf_private_ip(monkeypatch: pytest.MonkeyPatch) -> None:
    import socket

    from httpcore._backends.anyio import AnyIOBackend

    from src.infrastructure.network import SSRFProtectedBackend

    def mock_getaddrinfo(
        *args: object, **kwargs: object
    ) -> list[tuple[int, int, int, str, tuple[str, int]]]:
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("127.0.0.1", 80))]

    monkeypatch.setattr(socket, "getaddrinfo", mock_getaddrinfo)
    backend = SSRFProtectedBackend(AnyIOBackend(), allowed_hosts=["openrouter.ai"])
    with pytest.raises(ValueError, match="Disallowed private or loopback IP"):
        await backend.connect_tcp("openrouter.ai", 80)


@pytest.mark.asyncio
async def test_unix_socket() -> None:
    import contextlib

    from httpcore._backends.anyio import AnyIOBackend

    from src.infrastructure.network import SSRFProtectedBackend

    backend = SSRFProtectedBackend(AnyIOBackend(), allowed_hosts=["openrouter.ai"])
    with contextlib.suppress(Exception):
        await backend.connect_unix_socket("fake_path")


@pytest.mark.asyncio
async def test_secure_transport_allowed_hosts_validation() -> None:
    from src.infrastructure.network import SecureAsyncHTTPTransport

    with pytest.raises(
        ValueError, match="Invalid domain name in allowed_hosts: http://invalid-domain.com"
    ):
        SecureAsyncHTTPTransport(allowed_hosts=["http://invalid-domain.com"])

    with pytest.raises(ValueError, match="Invalid domain name in allowed_hosts: 127.0.0.1"):
        SecureAsyncHTTPTransport(allowed_hosts=["127.0.0.1"])

    # Should not raise
    SecureAsyncHTTPTransport(allowed_hosts=["openrouter.ai"])
    SecureAsyncHTTPTransport(allowed_hosts=["localhost"])
