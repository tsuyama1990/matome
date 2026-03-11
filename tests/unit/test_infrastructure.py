import os
from typing import Any
from unittest import mock

import httpx
import pytest
from cryptography.fernet import Fernet
from pydantic import SecretStr

from src.domain_models import CredentialConfig, PipelineConfig, SemanticChunk
from src.infrastructure.mock_vdb import MockVectorDB
from src.infrastructure.openrouter import OpenRouterGateway
from src.interfaces import LLMError


@pytest.fixture
def mock_env_key() -> Any:
    """Fixture to safely inject a valid encryption key for tests."""
    return mock.patch.dict(
        os.environ, {"MATOME_ENCRYPTION_KEY": Fernet.generate_key().decode("utf-8")}
    )


@pytest.fixture
def valid_config(mock_env_key: Any) -> PipelineConfig:
    with mock_env_key:
        valid_key = "sk-or-v1-" + ("C" * 64)
        config = PipelineConfig()
        config.credentials = CredentialConfig(openrouter_api_key=SecretStr(valid_key))
        return config


def test_openrouter_gateway_success(valid_config: PipelineConfig, httpx_mock: Any) -> None:
    gateway = OpenRouterGateway(config=valid_config)

    httpx_mock.add_response(
        json={"choices": [{"message": {"content": "Mocked LLM response"}}]},
        status_code=200,
    )

    response = gateway.invoke("Test prompt")
    assert response == "Mocked LLM response"


def test_openrouter_gateway_failure(valid_config: PipelineConfig, httpx_mock: Any) -> None:
    gateway = OpenRouterGateway(config=valid_config)

    # Note that the gateway retries 3 times, so we need to mock the response for all attempts.
    for _ in range(3):
        httpx_mock.add_response(status_code=500, json={"error": "Internal Server Error"})

    with pytest.raises(LLMError, match="OpenRouter API failed"):
        gateway.invoke("Test prompt")


def test_openrouter_gateway_timeout(valid_config: PipelineConfig, httpx_mock: Any) -> None:
    gateway = OpenRouterGateway(config=valid_config)

    for _ in range(3):
        httpx_mock.add_exception(httpx.TimeoutException("Timeout"))

    with pytest.raises(LLMError, match="Timeout connecting to OpenRouter"):
        gateway.invoke("Test prompt")


def test_openrouter_gateway_invalid_response(valid_config: PipelineConfig, httpx_mock: Any) -> None:
    gateway = OpenRouterGateway(config=valid_config)

    httpx_mock.add_response(json={"invalid_key": "No choices here"}, status_code=200)

    with pytest.raises(LLMError, match="Invalid response format from OpenRouter"):
        gateway.invoke("Test prompt")


def test_mock_vector_db_store_and_search() -> None:
    vdb = MockVectorDB()

    chunk1 = SemanticChunk(id="1", text="This is about AI.")
    chunk2 = SemanticChunk(id="2", text="This is about machine learning.")
    chunk3 = SemanticChunk(id="3", text="Python is a programming language.")

    vdb.store([chunk1, chunk2])
    vdb.store([chunk3])

    # Search for "AI" - because punctuation is not handled seamlessly in our basic mock, search for exact word
    results = vdb.search("AI.", top_k=2)
    assert len(results) == 1
    assert results[0].id == "1"

    # Search for "is"
    results_top_1 = vdb.search("is", top_k=1)
    assert len(results_top_1) == 1


def test_openrouter_gateway_request_error(valid_config: PipelineConfig, httpx_mock: Any) -> None:
    gateway = OpenRouterGateway(config=valid_config)

    for _ in range(3):
        httpx_mock.add_exception(httpx.RequestError("Network Error"))

    with pytest.raises(LLMError, match="Network error connecting to OpenRouter"):
        gateway.invoke("Test prompt")


def test_openrouter_gateway_missing_key(valid_config: PipelineConfig) -> None:
    valid_config.credentials.openrouter_api_key = None
    valid_config.credentials._encrypted_api_key = None
    gateway = OpenRouterGateway(config=valid_config)

    with pytest.raises(LLMError, match="Missing or invalid OpenRouter API key"):
        gateway.invoke("Test prompt")


def test_openrouter_gateway_missing_content(valid_config: PipelineConfig, httpx_mock: Any) -> None:
    gateway = OpenRouterGateway(config=valid_config)

    httpx_mock.add_response(
        json={"choices": [{"message": {"other": "No content here"}}]}, status_code=200
    )

    with pytest.raises(LLMError, match="Missing content in OpenRouter response"):
        gateway.invoke("Test prompt")


def test_mock_vector_db_semantic_search() -> None:
    vdb = MockVectorDB()

    chunk1 = SemanticChunk(id="1", text="Machine learning is fascinating")
    chunk2 = SemanticChunk(id="2", text="Deep learning and AI are powerful")
    chunk3 = SemanticChunk(id="3", text="Python programming is simple")
    chunk4 = SemanticChunk(id="4", text="I love machine learning very much")

    vdb.store([chunk1, chunk2, chunk3, chunk4])

    results = vdb.search("machine learning", top_k=2)
    assert len(results) == 2
    # chunk1 ("machine learning" -> 2 overlap, 5 union = 0.4)
    # chunk4 ("machine learning" -> 2 overlap, 6 union = 0.33)
    # Both should rank higher than the rest
    ids = [r.id for r in results]
    assert "1" in ids
    assert "4" in ids
    assert results[0].id == "1"  # Higher score


def test_openrouter_gateway_empty_prompt(valid_config: PipelineConfig) -> None:
    gateway = OpenRouterGateway(config=valid_config)

    with pytest.raises(ValueError, match="Prompt cannot be empty"):
        gateway.invoke("")


def test_openrouter_gateway_prompt_too_long(valid_config: PipelineConfig) -> None:
    gateway = OpenRouterGateway(config=valid_config)

    with pytest.raises(ValueError, match="Prompt length exceeds maximum allowed length"):
        gateway.invoke("a" * (valid_config.max_prompt_length + 1))


def test_openrouter_gateway_rate_limit(valid_config: PipelineConfig, httpx_mock: Any) -> None:
    valid_config.requests_per_minute_limit = 600  # 10 requests per second -> 0.1s interval
    gateway = OpenRouterGateway(config=valid_config)

    httpx_mock.add_response(json={"choices": [{"message": {"content": "ok"}}]}, status_code=200)
    httpx_mock.add_response(json={"choices": [{"message": {"content": "ok"}}]}, status_code=200)

    import time

    start = time.time()
    gateway.invoke("first")
    gateway.invoke("second")
    end = time.time()

    assert end - start >= 0.1


def test_openrouter_gateway_schema_validation_error(
    valid_config: PipelineConfig, httpx_mock: Any
) -> None:
    gateway = OpenRouterGateway(config=valid_config)
    httpx_mock.add_response(json={"choices": [{"bad": "data"}]}, status_code=200)

    with pytest.raises(LLMError, match="Invalid response format from OpenRouter"):
        gateway.invoke("Test prompt")


def test_infrastructure_init_factory(valid_config: PipelineConfig) -> None:
    from src.infrastructure import get_mock_vector_db, get_openrouter_gateway
    from src.infrastructure.mock_vdb import MockVectorDB
    from src.infrastructure.openrouter import OpenRouterGateway

    gw = get_openrouter_gateway(valid_config)
    assert isinstance(gw, OpenRouterGateway)

    vdb = get_mock_vector_db()
    assert isinstance(vdb, MockVectorDB)


def test_openrouter_gateway_rate_limit_zero(valid_config: PipelineConfig, httpx_mock: Any) -> None:
    valid_config.requests_per_minute_limit = 0
    gateway = OpenRouterGateway(config=valid_config)
    httpx_mock.add_response(json={"choices": [{"message": {"content": "ok"}}]}, status_code=200)
    gateway.invoke("first")  # Should return immediately with no sleep


def test_openrouter_gateway_network_error(valid_config: PipelineConfig, httpx_mock: Any) -> None:
    gateway = OpenRouterGateway(config=valid_config)

    for _ in range(3):
        httpx_mock.add_exception(httpx.RequestError("Network Error"))

    with pytest.raises(LLMError, match="Network error connecting to OpenRouter"):
        gateway.invoke("Test prompt")
