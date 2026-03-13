import logging
import uuid

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from src.config.settings import ModelConfig
from src.domain_models.exceptions import ProcessingError
from src.interfaces.dependencies import LLMProtocol

logger = logging.getLogger(__name__)


class OpenRouterClient(LLMProtocol):
    """Concrete implementation of LLMProtocol using OpenRouter."""

    def __init__(self, config: ModelConfig) -> None:
        self._api_key = config.openrouter_api_key.get_secret_value()
        self._model = config.text_fast_model
        # Use connection pooling
        self._client = httpx.AsyncClient(timeout=30.0)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((httpx.RequestError, httpx.HTTPStatusError)),
        reraise=True,
    )
    async def _make_request(
        self, payload: dict[str, str | list[dict[str, str]]], headers: dict[str, str]
    ) -> httpx.Response:
        response = await self._client.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers=headers,
            json=payload,
        )

        if response.status_code == 429:
            # Specific handling to trigger retry for rate limits
            response.raise_for_status()

        response.raise_for_status()
        return response

    async def generate(self, prompt: str) -> str:
        """Generates text from OpenRouter with retry logic."""
        correlation_id = str(uuid.uuid4())

        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

        payload: dict[str, str | list[dict[str, str]]] = {
            "model": self._model,
            "messages": [{"role": "user", "content": prompt}],
        }

        try:
            response = await self._make_request(payload, headers)
            data = response.json()
            return str(data["choices"][0]["message"]["content"])
        except httpx.HTTPStatusError as e:
            status_code = e.response.status_code
            logger.exception(
                "LLM HTTP error. Code: %s, Correlation ID: %s", status_code, correlation_id
            )

            # Sanitize error to prevent infrastructure leakage
            msg = f"LLM request failed with status {status_code}. (Trace: {correlation_id})"
            raise ProcessingError(msg) from e
        except httpx.RequestError as e:
            logger.exception("LLM network request error. Correlation ID: %s", correlation_id)
            msg = f"LLM connection failed. (Trace: {correlation_id})"
            raise ProcessingError(msg) from e
        except Exception as e:
            logger.exception("Unexpected LLM error. Correlation ID: %s", correlation_id)
            msg = f"LLM unexpected failure. (Trace: {correlation_id})"
            raise ProcessingError(msg) from e
