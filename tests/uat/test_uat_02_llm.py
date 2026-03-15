import httpx
import pytest

from src.domain_models.config import AppConfig, ModelRoutingRules
from src.infrastructure.openrouter import OpenRouterClient
from src.infrastructure.test_services import MockHttpxTransport


@pytest.fixture
def uat_config(monkeypatch: pytest.MonkeyPatch) -> AppConfig:
    monkeypatch.setenv(
        "OPENROUTER_API_KEY",
        "sk-or-v1-abcdef0123456789abcdef0123456789abcdef0123456789abcdef0123456789",
    )
    monkeypatch.setenv("TENANT_ID", "uat-tenant")
    return AppConfig(  # type: ignore[call-arg]
        routing_rules=ModelRoutingRules(
            text_fast_model="claude-3-opus",
            text_reasoning_model="claude-3-opus",
            multimodal_model="claude-3-opus",
            fallback_model="gpt-4o-mini",
        )
    )


@pytest.mark.asyncio
async def test_uat_02_01_successful_llm_text_generation(uat_config: AppConfig) -> None:
    """
    Scenario ID: UAT-02-01
    Title: Successful LLM Text Generation
    """
    transport = MockHttpxTransport()
    transport.add_response(
        status_code=200, json_data={"choices": [{"message": {"content": "Hello, world!"}}]}
    )
    client = httpx.AsyncClient(transport=transport)

    openrouter = OpenRouterClient(config=uat_config, client=client)
    result = await openrouter.generate_text("Say hello", "claude-3-opus")

    assert result == "Hello, world!"


@pytest.mark.asyncio
async def test_uat_02_02_network_resilience(uat_config: AppConfig) -> None:
    """
    Scenario ID: UAT-02-02
    Title: Network Resilience: Retries on Transient Errors
    """
    transport = MockHttpxTransport()
    # First: connection timeout
    transport.add_response(exc=httpx.ConnectTimeout("Timeout"))
    # Second: 502 Bad Gateway
    transport.add_response(status_code=502, json_data={})
    transport.add_response(
        status_code=200, json_data={"choices": [{"message": {"content": "Recovered!"}}]}
    )
    client = httpx.AsyncClient(transport=transport)

    openrouter = OpenRouterClient(config=uat_config, client=client)
    result = await openrouter.generate_text("Say hello", "claude-3-opus")

    assert result == "Recovered!"
    assert transport.call_count == 3


@pytest.mark.asyncio
async def test_uat_02_03_automatic_model_fallback(uat_config: AppConfig) -> None:
    """
    Scenario ID: UAT-02-03
    Title: High Availability: Automatic Model Fallback
    """
    transport = MockHttpxTransport()
    # Primary model (claude-3-opus) times out consistently (3 retries)
    transport.add_response(exc=httpx.ConnectTimeout("Timeout"))
    transport.add_response(exc=httpx.ConnectTimeout("Timeout"))
    transport.add_response(exc=httpx.ConnectTimeout("Timeout"))

    # Fallback model (gpt-4o-mini) succeeds
    transport.add_response(
        status_code=200, json_data={"choices": [{"message": {"content": "Fallback used"}}]}
    )
    client = httpx.AsyncClient(transport=transport)

    openrouter = OpenRouterClient(config=uat_config, client=client)
    result = await openrouter.generate_text("Say hello", "claude-3-opus")

    assert result == "Fallback used"
    # Ensure fallback was called (4th request) with the fallback model
    import json

    fallback_request_body = json.loads(transport.requests[3].content.decode("utf-8"))
    assert fallback_request_body["model"] == "gpt-4o-mini"
