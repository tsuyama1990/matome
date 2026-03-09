from src.domain_models import AIServiceProtocol, DocumentNode, PivotBoard, UserInteractionContext


class DefaultAIService(AIServiceProtocol):
    """Application-level AI orchestrator. Dispatches requests to external infrastructure."""

    def __init__(self, api_key: str | None = None, model: str = "google/gemini-2.5-flash") -> None:
        self.api_key = api_key
        self.model = model
        self.err_msg = "OpenRouter integration not fully implemented"
        self.err_msg_key = "OpenRouter integration not fully implemented without api_key"

    def generate_summary(self, content: str) -> str:
        if not self.api_key:
            raise NotImplementedError(self.err_msg_key)

        # Proper OpenRouter integration will be implemented via HTTP requests here
        raise NotImplementedError(self.err_msg)

    def generate_question(self, node: DocumentNode) -> str:
        if not self.api_key:
            raise NotImplementedError(self.err_msg_key)

        raise NotImplementedError(self.err_msg)

    def generate_mermaid_diagram(self, board: PivotBoard) -> str:
        raise NotImplementedError(self.err_msg)

    def evaluate_answer(self, context: UserInteractionContext) -> tuple[bool, str]:
        raise NotImplementedError(self.err_msg)
