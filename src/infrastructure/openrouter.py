import logging
import time
from typing import Any

import httpx
from pydantic import BaseModel, SecretStr

from src.domain_models import PipelineConfig
from src.interfaces import LLMError, LLMProtocol

logger = logging.getLogger(__name__)


class OpenRouterMessage(BaseModel):
    content: str | None = None


class OpenRouterChoice(BaseModel):
    message: OpenRouterMessage


class OpenRouterResponseSchema(BaseModel):
    choices: list[OpenRouterChoice]


class OpenRouterGateway(LLMProtocol):
    """An implementation of LLMProtocol that interfaces with the OpenRouter API."""

    def __init__(self, config: PipelineConfig) -> None:
        self.config = config
        self._last_request_time = 0.0

    def invoke(self, prompt: str, timeout: int = 30, retries: int = 3, **kwargs: Any) -> str:
        """Invokes the OpenRouter LLM with a prompt, timeout, and retry logic."""
        prompt = self._validate_and_sanitize_prompt(prompt)
        self._enforce_rate_limit()

        payload = self._prepare_payload(prompt, **kwargs)

        # To prevent exposing the plaintext key string in memory, we dynamically
        # supply a generator-based Auth object to the HTTPX client so the authorization
        # header is generated securely and immediately during request transmission.
        def auth_generator(request: httpx.Request) -> httpx.Request:
            decrypted_key: SecretStr | None = self.config.credentials.get_decrypted_api_key()
            if not decrypted_key:
                msg = "Missing or invalid OpenRouter API key"
                raise LLMError(msg)

            # This string exists only within the scope of this closure during transmission
            request.headers["Authorization"] = f"Bearer {decrypted_key.get_secret_value()}"

            # Other required headers
            request.headers["HTTP-Referer"] = self.config.app_domain
            request.headers["X-Title"] = self.config.app_title
            request.headers["Content-Type"] = "application/json"
            return request

        with httpx.Client(timeout=timeout, auth=auth_generator) as client:
            return self._execute_request(client, payload, retries)

    def _validate_and_sanitize_prompt(self, prompt: str) -> str:
        """Validates prompt length and strips dangerous null bytes."""
        if not prompt:
            msg = "Prompt cannot be empty"
            raise ValueError(msg)

        # Sanitize null bytes which could truncate C-based parsing behind the scenes
        sanitized_prompt = prompt.replace("\x00", "")

        if len(sanitized_prompt) > self.config.max_prompt_length:
            msg = f"Prompt length exceeds maximum allowed length of {self.config.max_prompt_length}"
            raise ValueError(msg)

        return sanitized_prompt

    def _enforce_rate_limit(self) -> None:
        """Enforces a simple rate limit based on configured limits."""
        if self.config.requests_per_minute_limit <= 0:
            return

        min_interval = 60.0 / self.config.requests_per_minute_limit
        elapsed = time.time() - self._last_request_time

        if elapsed < min_interval:
            sleep_time = min_interval - elapsed
            logger.debug(f"Rate limiting active, sleeping for {sleep_time:.2f} seconds")
            time.sleep(sleep_time)

        self._last_request_time = time.time()

    def _prepare_payload(self, prompt: str, **kwargs: Any) -> dict[str, Any]:
        model = kwargs.get("model", self.config.reasoning_model)

        payload = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
        }

        if "temperature" in kwargs:
            payload["temperature"] = kwargs["temperature"]
        if "max_tokens" in kwargs:
            payload["max_tokens"] = kwargs["max_tokens"]

        return payload

    def _execute_request(
        self, client: httpx.Client, payload: dict[str, Any], retries: int
    ) -> str:
        for attempt in range(retries):
            try:
                logger.debug(f"Sending request to OpenRouter (Attempt {attempt + 1}/{retries})")
                response = client.post(self.config.openrouter_endpoint, json=payload)
                response.raise_for_status()

                response_json = response.json()
                return self._parse_response(response_json)

            except httpx.TimeoutException as e:
                logger.warning(f"Timeout on attempt {attempt + 1}: {e}")
                if attempt == retries - 1:
                    msg = f"Timeout connecting to OpenRouter after {retries} attempts."
                    raise LLMError(msg) from e
            except httpx.HTTPStatusError as e:
                logger.warning(
                    f"HTTP Error {e.response.status_code} on attempt {attempt + 1}: {e.response.text}"
                )
                if attempt == retries - 1:
                    msg = f"OpenRouter API failed with status {e.response.status_code}: {e.response.text}"
                    raise LLMError(msg) from e
            except httpx.RequestError as e:
                logger.warning(f"Network Error on attempt {attempt + 1}: {e}")
                if attempt == retries - 1:
                    msg = f"Network error connecting to OpenRouter: {e}"
                    raise LLMError(msg) from e

        msg = "Failed to invoke OpenRouter after retries"
        raise LLMError(msg)

    def _parse_response(self, response_json: dict[str, Any]) -> str:
        try:
            # Validate against Pydantic schema
            validated_response = OpenRouterResponseSchema(**response_json)
        except Exception as e:
            logger.exception("Failed to validate OpenRouter response schema")
            msg = f"Invalid response format from OpenRouter: {response_json}"
            raise LLMError(msg) from e

        if not validated_response.choices:
            msg = f"Invalid response format from OpenRouter: {response_json}"
            raise LLMError(msg)

        content = validated_response.choices[0].message.content
        if content is None:
            msg = "Missing content in OpenRouter response"
            raise LLMError(msg)

        return str(content)
