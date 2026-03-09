from pydantic import SecretStr

from src.config import Settings
from src.domain_models import (
    AIServiceProtocol,
    DocumentNode,
    HTTPClientProtocol,
    PivotBoard,
    RetryPolicyProtocol,
    UserInteractionContext,
)


class DefaultAIService(AIServiceProtocol):
    """Application-level AI orchestrator. Dispatches requests to external infrastructure."""

    def __init__(
        self,
        settings: Settings | None = None,
        http_client: HTTPClientProtocol | None = None,
        retry_policy: RetryPolicyProtocol | None = None,
    ) -> None:
        from src.infrastructure.services import RequestsHTTPClient, TenacityRetryPolicy
        from src.utils.validation import validate_api_key_format

        if settings is None:
            settings = Settings()

        self.http_client = http_client or RequestsHTTPClient()
        self.retry_policy = retry_policy or TenacityRetryPolicy()

        self.settings = settings
        api_key = self.settings.openrouter_api_key

        if not api_key:
            msg = "A valid API Key is required to initialize DefaultAIService."
            raise ValueError(msg)

        raw_key = api_key.get_secret_value() if isinstance(api_key, SecretStr) else str(api_key)
        validated_key = validate_api_key_format(raw_key)
        if validated_key is None:
            raise ValueError(msg)

        self.api_key = SecretStr(validated_key)

    def _call_api(self, prompt: str, model: str | None = None) -> str:
        def _execute() -> str:
            headers = {
                "Authorization": f"Bearer {self.api_key.get_secret_value()}",
                "Content-Type": "application/json",
            }
            data = {
                "model": model or self.settings.text_fast_model,
                "messages": [{"role": "user", "content": prompt}],
            }
            result = self.http_client.post(
                self.settings.openrouter_api_url, json=data, headers=headers, timeout=10
            )
            return str(result["choices"][0]["message"]["content"])

        return str(self.retry_policy.execute(_execute))

    def generate_summary(self, content: str) -> str:
        prompt = (
            f"Summarize the following content comprehensively using Chain of Density:\n\n{content}"
        )
        return self._call_api(prompt, model=self.settings.text_fast_model)

    def generate_question(self, node: DocumentNode) -> str:
        prompt = f"Generate an engaging SQ3R question for the following content node:\n\n{node.title}\n{node.content.summary}"
        return self._call_api(prompt, model=self.settings.text_fast_model)

    def generate_mermaid_diagram(self, board: PivotBoard) -> str:
        prompt = f"Generate a Mermaid.js diagram based on this structure: {board.id} with axis {board.axis}"
        return self._call_api(prompt, model=self.settings.text_reasoning_model)

    def evaluate_answer(self, context: UserInteractionContext) -> tuple[bool, str]:
        prompt = f"Evaluate this user answer: '{context.user_answer}' for the question: '{context.question_asked}'. Is it basically correct? Start with YES or NO."
        response = self._call_api(prompt, model=self.settings.text_reasoning_model)
        is_correct = response.strip().upper().startswith("YES")
        return is_correct, response
