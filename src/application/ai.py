
from src.domain_models import (
    AIServiceProtocol,
    ContentNode,
    CredentialProviderProtocol,
    HTTPClientProtocol,
    IdentityNode,
    PivotBoard,
    RetryPolicyProtocol,
    UserInteractionContext,
)


class DefaultAIService(AIServiceProtocol):
    """Application-level AI orchestrator. Dispatches requests to external infrastructure."""

    def __init__(
        self,
        credential_provider: "CredentialProviderProtocol",
        api_url: str,
        text_fast_model: str,
        text_reasoning_model: str,
        ai_timeout: int,
        http_client: HTTPClientProtocol,
        retry_policy: RetryPolicyProtocol,
    ) -> None:
        self.http_client = http_client
        self.retry_policy = retry_policy
        self.api_url = api_url
        self.text_fast_model = text_fast_model
        self.text_reasoning_model = text_reasoning_model
        self.ai_timeout = ai_timeout
        self.credential_provider = credential_provider

    def _call_api(self, prompt: str, model: str | None = None) -> str:
        def _execute() -> str:
            headers = {
                "Authorization": f"Bearer {self.credential_provider.get_api_key()}",
                "Content-Type": "application/json",
            }
            data = {
                "model": model or self.text_fast_model,
                "messages": [{"role": "user", "content": prompt}],
            }
            result = self.http_client.post(
                self.api_url,
                json=data,
                headers=headers,
                timeout=self.ai_timeout,
            )
            return str(result["choices"][0]["message"]["content"])

        return str(self.retry_policy.execute(_execute))

    def generate_summary(self, content: str) -> str:
        prompt = (
            f"Summarize the following content comprehensively using Chain of Density:\n\n{content}"
        )
        return self._call_api(prompt, model=self.text_fast_model)

    def generate_question(self, identity: IdentityNode, content: ContentNode) -> str:
        prompt = f"Generate an engaging SQ3R question for the following content node:\n\n{identity.title}\n{content.summary}"
        return self._call_api(prompt, model=self.text_fast_model)

    def generate_mermaid_diagram(self, board: PivotBoard) -> str:
        prompt = f"Generate a Mermaid.js diagram based on this structure: {board.id} with axis {board.axis}"
        return self._call_api(prompt, model=self.text_reasoning_model)

    def evaluate_answer(self, context: UserInteractionContext) -> tuple[bool, str]:
        prompt = f"Evaluate this user answer: '{context.user_answer}' for the question: '{context.question_asked}'. Is it basically correct? Start with YES or NO."
        response = self._call_api(prompt, model=self.text_reasoning_model)
        is_correct = response.strip().upper().startswith("YES")
        return is_correct, response
