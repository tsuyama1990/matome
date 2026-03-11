from typing import Any

import httpx
from pydantic import SecretStr

from src.domain_models import PipelineConfig
from src.interfaces import LLMError, LLMProtocol


class OpenRouterGateway(LLMProtocol):
    """An implementation of LLMProtocol that interfaces with the OpenRouter API."""

    def __init__(self, config: PipelineConfig) -> None:
        self.config = config
        self.endpoint = "https://openrouter.ai/api/v1/chat/completions"

    def invoke(self, prompt: str, timeout: int = 30, retries: int = 3, **kwargs: Any) -> str:
        """Invokes the OpenRouter LLM with a prompt, timeout, and retry logic."""
        headers = self._prepare_headers()
        payload = self._prepare_payload(prompt, **kwargs)

        with httpx.Client(timeout=timeout) as client:
            return self._execute_request(client, payload, headers, retries)

    def _prepare_headers(self) -> dict[str, str]:
        decrypted_key: SecretStr | None = self.config.credentials.get_decrypted_api_key()
        if not decrypted_key:
            msg = "Missing or invalid OpenRouter API key"
            raise LLMError(msg)

        return {
            "Authorization": f"Bearer {decrypted_key.get_secret_value()}",
            "HTTP-Referer": "https://matome.test",  # Required by OpenRouter
            "X-Title": "matome",  # Optional, but good practice
            "Content-Type": "application/json",
        }

    def _prepare_payload(self, prompt: str, **kwargs: Any) -> dict[str, Any]:
        # Select model from kwargs or use default reasoning model
        model = kwargs.get("model", self.config.reasoning_model)

        payload = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
        }

        # Add any extra kwargs supported by OpenRouter
        if "temperature" in kwargs:
            payload["temperature"] = kwargs["temperature"]
        if "max_tokens" in kwargs:
            payload["max_tokens"] = kwargs["max_tokens"]

        return payload

    def _execute_request(
        self, client: httpx.Client, payload: dict[str, Any], headers: dict[str, str], retries: int
    ) -> str:
        for attempt in range(retries):
            try:
                response = client.post(self.endpoint, headers=headers, json=payload)
                response.raise_for_status()

                response_json = response.json()
                return self._parse_response(response_json)

            except httpx.TimeoutException as e:
                if attempt == retries - 1:
                    msg = f"Timeout connecting to OpenRouter after {retries} attempts."
                    raise LLMError(msg) from e
            except httpx.HTTPStatusError as e:
                if attempt == retries - 1:
                    msg = f"OpenRouter API failed with status {e.response.status_code}: {e.response.text}"
                    raise LLMError(msg) from e
            except httpx.RequestError as e:
                if attempt == retries - 1:
                    msg = f"Network error connecting to OpenRouter: {e}"
                    raise LLMError(msg) from e

        msg = "Failed to invoke OpenRouter after retries"
        raise LLMError(msg)

    def _parse_response(self, response_json: dict[str, Any]) -> str:
        if "choices" not in response_json or not response_json["choices"]:
            msg = f"Invalid response format from OpenRouter: {response_json}"
            raise LLMError(msg)

        content = response_json["choices"][0].get("message", {}).get("content")
        if content is None:
            msg = "Missing content in OpenRouter response"
            raise LLMError(msg)

        return str(content)
