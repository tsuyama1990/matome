import logging
from typing import Any

import httpx
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
)

from src.domain_models.config import AppConfig
from src.domain_models.exceptions import LLMAuthenticationError, LLMConnectionError, LLMServerError
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
        self._api_key = config.openrouter_api_key
        self._base_url = config.openrouter_base_url
        self._client = client or httpx.AsyncClient(timeout=30.0)

    def _handle_invalid_response(self) -> str:
        msg = "Invalid response format: 'choices' missing or empty."
        raise ValueError(msg)

    def _is_transient_error(self, e: Exception) -> bool:
        """Determines if the exception is transient and should trigger a retry."""
        if isinstance(e, (httpx.ConnectError, httpx.TimeoutException)):
            return True
        if isinstance(e, httpx.HTTPStatusError):
            return e.response.status_code in (500, 502, 503, 504)
        return False

    @staticmethod
    def _should_retry(retry_state: Any) -> bool:
        """Custom retry condition to skip LLMAuthenticationError."""
        if retry_state.outcome.failed:
            e = retry_state.outcome.exception()
            return not isinstance(e, LLMAuthenticationError)
        return False

    @retry(
        retry=_should_retry,
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True,
    )
    async def _make_request(self, prompt: str, model: str) -> str:
        """Makes an asynchronous HTTP request to OpenRouter with retries for transient errors."""
        headers = {
            "Authorization": f"Bearer {self._api_key.get_secret_value()}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
        }

        try:
            response = await self._client.post(
                self._base_url, headers=headers, json=payload, timeout=30.0
            )
            response.raise_for_status()

            data = response.json()
            # Ensure "choices" is in data and it's not empty, otherwise raise a ValueError
            if "choices" not in data or not data["choices"]:
                return self._handle_invalid_response()

            return str(data["choices"][0]["message"]["content"])

        except httpx.HTTPStatusError as e:
            if e.response.status_code in (401, 403):
                msg = "Authentication failed. Please verify the API key."
                # We bypass Tenacity by wrapping in a custom error that is NOT retried.
                raise LLMAuthenticationError(msg) from e

            if self._is_transient_error(e):
                logger.warning("Transient error occurred during LLM request. Retrying...")
                raise  # Let tenacity handle the retry

            if e.response.status_code >= 500:
                msg = "The external LLM service is currently unavailable."
                raise LLMServerError(msg) from e
            msg = "A generic HTTP error occurred during the LLM request."
            raise LLMConnectionError(msg) from e

        except (httpx.ConnectError, httpx.TimeoutException, httpx.RequestError) as e:
            if self._is_transient_error(e):
                logger.warning("Transient error occurred during LLM request. Retrying...")
                raise  # Let tenacity handle the retry
            msg = "A network timeout or connection error occurred."
            raise LLMConnectionError(msg) from e

        except Exception as e:
            msg = "An unexpected error occurred during LLM generation."
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
        except Exception as e:
            if isinstance(e, LLMAuthenticationError):
                raise

            if not self._is_transient_error(e):
                raise  # Re-raise non-transient, non-retryable errors immediately

            fallback = self._config.routing_rules.fallback_model
            logger.warning(
                f"Primary model {model} failed after retries due to {type(e).__name__}. "
                f"Attempting fallback to {fallback}."
            )
            try:
                return await self._make_request(prompt, fallback)
            except Exception as fallback_error:
                msg = "Both primary and fallback models failed to complete the request."
                raise LLMConnectionError(msg) from fallback_error
