from src.domain_models import (
    AIServiceProtocol,
    ContentNode,
    IdentityNode,
    PivotBoard,
    UserInteractionContext,
)
from src.domain_models.interfaces import AICommunicationClientProtocol, AISecurityScannerProtocol


class DefaultAIService(AIServiceProtocol):
    """Application-level AI orchestrator. Dispatches requests to external infrastructure."""

    def __init__(
        self,
        security_scanner: AISecurityScannerProtocol,
        communication_client: AICommunicationClientProtocol,
        text_fast_model: str,
        text_reasoning_model: str,
    ) -> None:
        self.security_scanner = security_scanner
        self.communication_client = communication_client
        self.text_fast_model = text_fast_model
        self.text_reasoning_model = text_reasoning_model

    def generate_summary(self, content: str) -> str:
        safe_content = self.security_scanner.sanitize(content)
        prompt = f"Summarize the following content comprehensively using Chain of Density:\n\n{safe_content}"
        return self.communication_client.call_api(prompt, model=self.text_fast_model)

    def generate_question(self, identity: IdentityNode, content: ContentNode) -> str:
        safe_title = self.security_scanner.sanitize(identity.title)
        safe_summary = self.security_scanner.sanitize(content.summary)
        prompt = f"Generate an engaging SQ3R question for the following content node:\n\n{safe_title}\n{safe_summary}"
        return self.communication_client.call_api(prompt, model=self.text_fast_model)

    def generate_mermaid_diagram(self, board: PivotBoard) -> str:
        safe_id = self.security_scanner.sanitize(str(board.id))
        safe_axis = self.security_scanner.sanitize(
            str(board.axis.value if hasattr(board.axis, "value") else board.axis)
        )
        prompt = f"Generate a Mermaid.js diagram based on this structure: {safe_id} with axis {safe_axis}"
        return self.communication_client.call_api(prompt, model=self.text_reasoning_model)

    def generate_markdown_requirements(self, board: PivotBoard) -> str:
        safe_id = self.security_scanner.sanitize(str(board.id))
        safe_axis = self.security_scanner.sanitize(
            str(board.axis.value if hasattr(board.axis, "value") else board.axis)
        )
        prompt = f"Generate a detailed Markdown Requirements Document (PRD) based on this structure: {safe_id} structured along axis {safe_axis}."
        return self.communication_client.call_api(prompt, model=self.text_reasoning_model)

    def verify_web_grounding(self, content: str) -> str:
        safe_content = self.security_scanner.sanitize(content)
        prompt = f"Cross-reference the following logic with modern SaaS best practices and web facts. Highlight any biases or outdated practices:\n\n{safe_content}"
        return self.communication_client.call_api(prompt, model=self.text_reasoning_model)

    def evaluate_answer(self, context: UserInteractionContext) -> tuple[bool, str]:
        safe_answer = self.security_scanner.sanitize(context.user_answer)
        safe_question = self.security_scanner.sanitize(context.question_asked)
        prompt = f"Evaluate this user answer: '{safe_answer}' for the question: '{safe_question}'. Is it basically correct? Start with YES or NO."
        response = self.communication_client.call_api(prompt, model=self.text_reasoning_model)
        is_correct = response.strip().upper().startswith("YES")
        return is_correct, response
