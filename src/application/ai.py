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

    def _sanitize_input(self, text: str | None) -> str:
        """Sanitize user input to prevent prompt injection and ensure safety."""
        import re

        if not text:
            return ""
        # Remove null bytes and limit length to prevent massive prompt abuse
        sanitized = text.replace("\x00", "").strip()[:50000]
        # Basic prompt injection mitigation: neutralizing system instruction keywords
        sanitized = re.sub(
            r"(?i)\b(ignore previous instructions|system prompt|you are a)\b",
            "[REDACTED]",
            sanitized,
        )
        # Escape markdown backticks to prevent breaking prompt formatting
        return sanitized.replace("```", "'''")

    def _call_api(self, prompt: str, model: str | None = None) -> str:
        def _execute() -> str:
            api_key = self.credential_provider.get_api_key()
            headers = {
                "Authorization": f"Bearer {api_key}",
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
                verify=True,  # Explicitly force SSL/TLS certificate validation
            )

            # Response validation
            if not isinstance(result, dict) or "choices" not in result:
                msg = "Unexpected API response format: missing 'choices'."
                raise ValueError(msg)

            choices = result.get("choices", [])
            if not choices or not isinstance(choices, list):
                msg = "Unexpected API response format: 'choices' is empty or invalid."
                raise ValueError(msg)

            message = choices[0].get("message", {})
            content = message.get("content")

            if content is None:
                msg = "Unexpected API response format: missing 'content'."
                raise ValueError(msg)

            return str(content)

        return str(self.retry_policy.execute(_execute))

    def generate_summary(self, content: str) -> str:
        safe_content = self._sanitize_input(content)
        prompt = f"Summarize the following content comprehensively using Chain of Density:\n\n{safe_content}"
        return self._call_api(prompt, model=self.text_fast_model)

    def generate_question(self, identity: IdentityNode, content: ContentNode) -> str:
        safe_title = self._sanitize_input(identity.title)
        safe_summary = self._sanitize_input(content.summary)
        prompt = f"Generate an engaging SQ3R question for the following content node:\n\n{safe_title}\n{safe_summary}"
        return self._call_api(prompt, model=self.text_fast_model)

    def generate_mermaid_diagram(self, board: PivotBoard) -> str:
        safe_id = self._sanitize_input(str(board.id))
        safe_axis = self._sanitize_input(
            str(board.axis.value if hasattr(board.axis, "value") else board.axis)
        )
        prompt = f"Generate a Mermaid.js diagram based on this structure: {safe_id} with axis {safe_axis}"
        return self._call_api(prompt, model=self.text_reasoning_model)

    def generate_markdown_requirements(self, board: PivotBoard) -> str:
        safe_id = self._sanitize_input(str(board.id))
        safe_axis = self._sanitize_input(
            str(board.axis.value if hasattr(board.axis, "value") else board.axis)
        )
        prompt = f"Generate a detailed Markdown Requirements Document (PRD) based on this structure: {safe_id} structured along axis {safe_axis}."
        return self._call_api(prompt, model=self.text_reasoning_model)

    def verify_web_grounding(self, content: str) -> str:
        safe_content = self._sanitize_input(content)
        prompt = f"Cross-reference the following logic with modern SaaS best practices and web facts. Highlight any biases or outdated practices:\n\n{safe_content}"
        return self._call_api(prompt, model=self.text_reasoning_model)

    def evaluate_answer(self, context: UserInteractionContext) -> tuple[bool, str]:
        safe_answer = self._sanitize_input(context.user_answer)
        safe_question = self._sanitize_input(context.question_asked)
        prompt = f"Evaluate this user answer: '{safe_answer}' for the question: '{safe_question}'. Is it basically correct? Start with YES or NO."
        response = self._call_api(prompt, model=self.text_reasoning_model)
        is_correct = response.strip().upper().startswith("YES")
        return is_correct, response
