from typing import Any

import requests
from pydantic import SecretStr

from src.domain_models import (
    AIServiceError,
    AIServiceProtocol,
    DocumentNode,
    PivotBoard,
    UserInteractionContext,
)


class DefaultAIService(AIServiceProtocol):
    """Application-level AI orchestrator. Dispatches requests to external infrastructure."""

    def __init__(self, api_key: str | SecretStr, model: str = "google/gemini-2.5-flash", api_url: str = "https://openrouter.ai/api/v1/chat/completions") -> None:
        from src.utils.validation import validate_api_key_format

        raw_key = api_key.get_secret_value() if isinstance(api_key, SecretStr) else str(api_key)

        if not raw_key:
            msg = "A valid API Key is required to initialize DefaultAIService."
            raise ValueError(msg)

        validated_key = validate_api_key_format(raw_key)
        if validated_key is None:
            raise ValueError(msg)

        self.api_key = SecretStr(validated_key)
        self.model = model
        self.api_url = api_url

    def _call_api(self, prompt: str) -> str:
        from tenacity import retry, stop_after_attempt, wait_exponential_jitter

        @retry(
            stop=stop_after_attempt(3),
            wait=wait_exponential_jitter(initial=1, max=10),
            reraise=True
        )
        def _execute() -> str:
            headers = {
                "Authorization": f"Bearer {self.api_key.get_secret_value()}",
                "Content-Type": "application/json",
            }
            data = {
                "model": self.model,
                "messages": [{"role": "user", "content": prompt}],
            }
            try:
                response = requests.post(self.api_url, json=data, headers=headers, timeout=10)
                response.raise_for_status()
                result: dict[str, Any] = response.json()
                return str(result["choices"][0]["message"]["content"])
            except requests.Timeout as e:
                msg = "The AI service request timed out."
                raise AIServiceError(msg) from e
            except requests.HTTPError as e:
                msg = f"The AI service returned an HTTP error: {e}"
                raise AIServiceError(msg) from e
            except requests.RequestException as e:
                msg = f"Failed to communicate with AI service: {e}"
                raise AIServiceError(msg) from e

        return _execute()

    def generate_summary(self, content: str) -> str:
        prompt = f"Summarize the following content comprehensively using Chain of Density:\n\n{content}"
        return self._call_api(prompt)

    def generate_question(self, node: DocumentNode) -> str:
        prompt = f"Generate an engaging SQ3R question for the following content node:\n\n{node.title}\n{node.content.summary}"
        return self._call_api(prompt)

    def generate_mermaid_diagram(self, board: PivotBoard) -> str:
        prompt = f"Generate a Mermaid.js diagram based on this structure: {board.id} with axis {board.axis}"
        return self._call_api(prompt)

    def evaluate_answer(self, context: UserInteractionContext) -> tuple[bool, str]:
        prompt = f"Evaluate this user answer: '{context.user_answer}' for the question: '{context.question_asked}'. Is it basically correct? Start with YES or NO."
        response = self._call_api(prompt)
        is_correct = response.strip().upper().startswith("YES")
        return is_correct, response
