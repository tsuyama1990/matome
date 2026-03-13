import logging
import os

import httpx

from src.config.settings import ModelConfig

logger = logging.getLogger(__name__)


class LLMError(Exception):
    """Custom exception for LLM operations."""


class OpenRouterGateway:
    """Gateway for OpenRouter API."""

    def __init__(self, config: ModelConfig) -> None:
        self._config = config
        self._client = httpx.AsyncClient(timeout=30.0)

    async def generate(self, prompt: str) -> str:
        """Generates text from a prompt."""
        api_key = os.environ.get("OPENROUTER_API_KEY")
        if not api_key:
            msg = "OPENROUTER_API_KEY environment variable is missing"
            raise ValueError(msg)

        headers = {
            "Authorization": f"Bearer {api_key}",
            "HTTP-Referer": "https://github.com/matome",
            "X-Title": "matome",
        }

        payload = {
            "model": self._config.text_reasoning_model,
            "messages": [{"role": "user", "content": prompt}]
        }

        try:
            response = await self._client.post(
                self._config.openrouter_api_url,
                json=payload,
                headers=headers,
            )
            response.raise_for_status()

            data = response.json()
            return str(data["choices"][0]["message"]["content"])

        except httpx.HTTPStatusError as e:
            # Sanitize error
            logger.exception("HTTP status error during LLM generation. Check API key and quota.")
            msg = "LLM API request failed due to an HTTP error."
            raise LLMError(msg) from e
        except httpx.RequestError as e:
            logger.exception("Network request error during LLM generation.")
            msg = "LLM API request failed due to a network error."
            raise LLMError(msg) from e

    async def close(self) -> None:
        """Close the async client."""
        await self._client.aclose()
