import httpx

from src.config.settings import ModelConfig
from src.domain_models.exceptions import ProcessingError
from src.interfaces.dependencies import LLMProtocol


class OpenRouterClient(LLMProtocol):
    """Concrete implementation of LLMProtocol using OpenRouter."""

    def __init__(self, config: ModelConfig) -> None:
        self._api_key = config.openrouter_api_key.get_secret_value()
        self._model = config.text_fast_model
        # Use connection pooling
        self._client = httpx.AsyncClient(timeout=30.0)

    async def generate(self, prompt: str) -> str:
        """Generates text from OpenRouter."""
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "http://localhost:8000",
            "X-Title": "matome",
        }

        payload = {
            "model": self._model,
            "messages": [{"role": "user", "content": prompt}],
        }

        try:
            response = await self._client.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers=headers,
                json=payload,
            )
            response.raise_for_status()
            data = response.json()
            return str(data["choices"][0]["message"]["content"])
        except httpx.HTTPStatusError as e:
            # Sanitize error to prevent infrastructure leakage
            msg = "LLM request failed."
            raise ProcessingError(msg) from e
        except Exception as e:
            msg = "LLM connection failed."
            raise ProcessingError(msg) from e
