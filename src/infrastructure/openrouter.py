import logging
from typing import Any

import httpx
from pydantic import SecretStr

from src.domain_models.config import AppConfig
from src.domain_models.exceptions import LLMAuthenticationError, LLMConnectionError, LLMServerError
from src.interfaces.llm_protocol import LLMProtocol

logger = logging.getLogger(__name__)


class OpenRouterAuth(httpx.Auth):
    """Custom httpx authentication to securely handle SecretStr injection."""

    def __init__(self, token: SecretStr) -> None:
        self.token = token

    def auth_flow(self, request: httpx.Request) -> Any:
        # Resolve actual token specifically at request time so it avoids log dumps
        actual_token = self.token.get_secret_value()
        request.headers["Authorization"] = f"Bearer {actual_token}"
        yield request


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

        if client is not None:
            self._client = client
        else:
            self._client = httpx.AsyncClient(timeout=self._config.llm_timeout)

    def _handle_invalid_response(self) -> str:
        msg = "Invalid response format: 'choices' missing or empty."
        raise ValueError(msg)

    def _handle_massive_payload(self) -> None:
        msg = "Generated text is suspiciously large."
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

    async def _make_request(self, prompt: str, model: str) -> str:
        """Makes an asynchronous HTTP request to OpenRouter with retries for transient errors."""
        import tenacity

        # Dynamically apply tenacity decorator using class config variables for retries
        retry_decorator = tenacity.retry(
            retry=self._should_retry,
            stop=tenacity.stop_after_attempt(self._config.max_retry_attempts),
            wait=tenacity.wait_exponential(
                multiplier=1, min=self._config.retry_min_wait, max=self._config.retry_max_wait
            ),
            reraise=True,
        )

        @retry_decorator
        async def _execute_request() -> str:
            headers = {
                "Content-Type": "application/json",
            }
            payload = {
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
            }

            try:
                response = await self._client.post(
                    self._base_url,
                    headers=headers,
                    json=payload,
                    timeout=self._config.llm_timeout,
                    auth=OpenRouterAuth(self._api_key),
                )
                response.raise_for_status()

                data = response.json()
                # Ensure "choices" is in data and it's not empty, otherwise raise a ValueError
                if "choices" not in data or not data["choices"]:
                    return self._handle_invalid_response()

                content = str(data["choices"][0]["message"]["content"])

                # Security: Validate the response content is reasonable and doesn't contain injected malicious instructions
                # or massive payloads that could cause downstream denial of service.
                if len(content) > self._config.max_content_length:
                    self._handle_massive_payload()

                import bleach

                # Sanitize the output to prevent injection attacks if this content is directly rendered in UI or parsed
                return bleach.clean(content, tags=[], attributes={}, protocols=[], strip=True)

            except Exception as e:
                self._handle_request_error(e)
                raise

        return await _execute_request()

    def _handle_request_error(self, e: Exception) -> None:
        import httpx

        if isinstance(e, httpx.HTTPStatusError):
            if e.response.status_code in (401, 403):
                msg = "Authentication failed. Please verify the API key."
                # We bypass Tenacity by wrapping in a custom error that is NOT retried.
                raise LLMAuthenticationError(msg) from e

            if self._is_transient_error(e):
                logger.warning("Transient error occurred during LLM request. Retrying...")
                raise e  # Let tenacity handle the retry

            if e.response.status_code >= 500:
                msg = "The external LLM service is currently unavailable."
                raise LLMServerError(msg) from e

            msg = "A generic HTTP error occurred during the LLM request."
            raise LLMConnectionError(msg) from e

        if isinstance(e, (httpx.ConnectError, httpx.TimeoutException, httpx.RequestError)):
            if self._is_transient_error(e):
                logger.warning("Transient error occurred during LLM request. Retrying...")
                raise e  # Let tenacity handle the retry
            msg = "A network timeout or connection error occurred."
            raise LLMConnectionError(msg) from e

        msg = "An unexpected error occurred during LLM generation."
        raise LLMConnectionError(msg) from e

    async def generate(self, prompt: str) -> str:
        return await self.generate_text(prompt, self._config.routing_rules.fallback_model)

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
