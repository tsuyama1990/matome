import json
import urllib.request
from typing import Any

from src.domain_models import AIServiceProtocol, DocumentNode, PivotBoard, UserInteractionContext


class DefaultAIService(AIServiceProtocol):
    """Application-level AI orchestrator. Dispatches requests to external infrastructure."""

    def __init__(self, api_key: str | None = None, model: str = "google/gemini-2.5-flash") -> None:
        self.api_key = api_key
        self.model = model

    def _call_api(self, prompt: str) -> str:
        if not self.api_key:
            # Fallback to a mock response if no API key is provided
            return f"Mocked AI Response for prompt: {prompt[:30]}..."

        url = "https://openrouter.ai/api/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        data = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
        }
        req = urllib.request.Request(  # noqa: S310
            url, data=json.dumps(data).encode("utf-8"), headers=headers, method="POST"
        )
        try:
            with urllib.request.urlopen(req) as response:  # noqa: S310
                result: dict[str, Any] = json.loads(response.read().decode("utf-8"))
                return str(result["choices"][0]["message"]["content"])
        except Exception as e:
            return f"API Error: {e}"

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
