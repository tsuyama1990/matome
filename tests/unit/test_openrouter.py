import httpx
import pytest

from src.domain_models.config import AppConfig, ModelRoutingRules
from src.domain_models.exceptions import LLMAuthenticationError, LLMConnectionError
from src.infrastructure.openrouter import OpenRouterClient
from src.infrastructure.test_services import MockHttpxTransport


@pytest.fixture
def test_config(monkeypatch: pytest.MonkeyPatch) -> AppConfig:
    monkeypatch.setenv(
        "OPENROUTER_API_KEY",
        "sk-or-v1-0000000000000000000000000000000000000000000000000000000000000000",
    )
    monkeypatch.setenv("TENANT_ID", "test-tenant")
    return AppConfig(  # type: ignore[call-arg]
        routing_rules=ModelRoutingRules(
            text_fast_model="fast-model",
            text_reasoning_model="reasoning-model",
            multimodal_model="vision-model",
            fallback_model="fallback-model",
        )
    )


@pytest.mark.asyncio
async def test_openrouter_happy_path(test_config: AppConfig) -> None:
    transport = MockHttpxTransport()
    transport.add_response(
        status_code=200, json_data={"choices": [{"message": {"content": "Hello World"}}]}
    )
    client = httpx.AsyncClient(transport=transport)  # type: ignore[arg-type]

    openrouter = OpenRouterClient(config=test_config, client=client)
    result = await openrouter.generate_text("Say hello", "fast-model")

    assert result == "Hello World"
    assert transport.call_count == 1
    # Check if the primary model was used in the payload
    import json

    request_body = json.loads(transport.requests[0].content.decode("utf-8"))
    assert request_body["model"] == "fast-model"


@pytest.mark.asyncio
async def test_openrouter_retries_on_transient_error(test_config: AppConfig) -> None:
    transport = MockHttpxTransport()
    transport.add_response(exc=httpx.ConnectTimeout("Timeout"))
    transport.add_response(status_code=502, json_data={})
    transport.add_response(
        status_code=200, json_data={"choices": [{"message": {"content": "Recovered!"}}]}
    )
    client = httpx.AsyncClient(transport=transport)  # type: ignore[arg-type]

    openrouter = OpenRouterClient(config=test_config, client=client)
    result = await openrouter.generate_text("Say hello", "fast-model")

    assert result == "Recovered!"
    assert transport.call_count == 3


@pytest.mark.asyncio
async def test_openrouter_immediate_failure_401(test_config: AppConfig) -> None:
    transport = MockHttpxTransport()
    # The HTTPStatusError is what triggers the 401 check, so we need to raise it
    req = httpx.Request("POST", "https://openrouter.ai/api/v1/chat/completions")
    resp = httpx.Response(401, request=req)
    transport.add_response(exc=httpx.HTTPStatusError("401", request=req, response=resp))
    client = httpx.AsyncClient(transport=transport)  # type: ignore[arg-type]

    openrouter = OpenRouterClient(config=test_config, client=client)

    with pytest.raises(
        LLMAuthenticationError, match="Authentication failed. Please verify the API key."
    ):
        await openrouter._make_request("Say hello", "fast-model")

    # Assert no retries on 401
    assert transport.call_count == 1


@pytest.mark.asyncio
async def test_openrouter_fallback_mechanism(test_config: AppConfig) -> None:
    transport = MockHttpxTransport()
    # Let the primary model fail all 3 retries
    transport.add_response(exc=httpx.ConnectTimeout("Timeout"))
    transport.add_response(exc=httpx.ConnectTimeout("Timeout"))
    transport.add_response(exc=httpx.ConnectTimeout("Timeout"))

    # Add a successful response for the fallback model
    transport.add_response(
        status_code=200, json_data={"choices": [{"message": {"content": "Fallback used"}}]}
    )
    client = httpx.AsyncClient(transport=transport)  # type: ignore[arg-type]

    openrouter = OpenRouterClient(config=test_config, client=client)
    result = await openrouter.generate_text("Say hello", "fast-model")

    assert result == "Fallback used"
    # 3 retries for primary + 1 for fallback = 4 calls total
    assert transport.call_count == 4

    import json

    fallback_request_body = json.loads(transport.requests[3].content.decode("utf-8"))
    assert fallback_request_body["model"] == "fallback-model"


@pytest.mark.asyncio
async def test_openrouter_fallback_fails(test_config: AppConfig) -> None:
    transport = MockHttpxTransport()
    # Let the primary model fail all 3 retries
    transport.add_response(exc=httpx.ConnectTimeout("Timeout"))
    transport.add_response(exc=httpx.ConnectTimeout("Timeout"))
    transport.add_response(exc=httpx.ConnectTimeout("Timeout"))

    # Let the fallback model fail too (and exhaust its 3 retries because _make_request retries it)
    transport.add_response(exc=httpx.ConnectError("Failed to connect"))
    transport.add_response(exc=httpx.ConnectError("Failed to connect"))
    transport.add_response(exc=httpx.ConnectError("Failed to connect"))

    client = httpx.AsyncClient(transport=transport)  # type: ignore[arg-type]

    openrouter = OpenRouterClient(config=test_config, client=client)

    with pytest.raises(LLMConnectionError, match="Both primary"):
        await openrouter.generate_text("Say hello", "fast-model")
