import logging

import httpx
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from src.domain_models.config import AppConfig
from src.domain_models.exceptions import LLMAuthenticationError, LLMConnectionError
from src.interfaces.llm_protocol import LLMProtocol

logger = logging.getLogger(__name__)


class OpenRouterClient(LLMProtocol):
    """Concrete implementation of LLMProtocol using OpenRouter."""

    def __init__(self, config: AppConfig, client: httpx.AsyncClient | None = None) -> None:
        """
        Initializes the OpenRouterClient.

        Args:
            config (AppConfig): Application configuration.
            client (httpx.AsyncClient | None): Optional injected HTTP client for testing.
        """
        self._config = config
        self._api_key = config.openrouter_api_key.get_secret_value()
        self._base_url = config.openrouter_base_url
        self._client = client or httpx.AsyncClient(timeout=30.0)

    def _handle_invalid_response(self) -> str:
        msg = "Invalid response format: 'choices' missing or empty."
        raise ValueError(msg)

    @retry(
        retry=retry_if_exception_type((httpx.ConnectError, httpx.TimeoutException)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True,
    )
    async def _make_request(self, prompt: str, model: str) -> str:
        """Makes an asynchronous HTTP request to OpenRouter with retries for transient errors."""
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
        }

        try:
            response = await self._client.post(self._base_url, headers=headers, json=payload)
            response.raise_for_status()

            data = response.json()
            # Ensure "choices" is in data and it's not empty, otherwise raise a ValueError
            if "choices" not in data or not data["choices"]:
                return self._handle_invalid_response()

            return str(data["choices"][0]["message"]["content"])

        except httpx.HTTPStatusError as e:
            if e.response.status_code in (401, 403):
                msg = f"Authentication failed with status {e.response.status_code}."
                raise LLMAuthenticationError(msg) from e
            if e.response.status_code in (500, 502, 503, 504):
                # We can just raise ConnectError to trigger a retry
                msg = f"Server error {e.response.status_code}"
                raise httpx.ConnectError(msg) from e
            msg = f"HTTP error {e.response.status_code} during LLM generation."
            raise LLMConnectionError(msg) from e

        except (httpx.ConnectError, httpx.TimeoutException) as e:
            logger.warning(f"Transient error occurred: {e}. Retrying...")
            raise

        except Exception as e:
            msg = f"Unexpected error during LLM generation: {e}"
            raise LLMConnectionError(msg) from e

    async def generate_text(self, prompt: str, model: str) -> str:
        """
        Generates text using the specified model, with fallback handling.

        Args:
            prompt (str): The prompt to send.
            model (str): The primary model to use.

        Returns:
            str: The generated text.
        """
        try:
            return await self._make_request(prompt, model)
        except (httpx.ConnectError, httpx.TimeoutException) as e:
            fallback = self._config.routing_rules.fallback_model
            logger.warning(
                f"Primary model {model} failed after retries due to {e}. "
                f"Attempting fallback to {fallback}."
            )
            try:
                return await self._make_request(prompt, fallback)
            except Exception as fallback_error:
                msg = f"Both primary ({model}) and fallback ({fallback}) models failed."
                raise LLMConnectionError(msg) from fallback_error
