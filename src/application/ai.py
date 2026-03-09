from src.domain_models import AIServiceProtocol, DocumentNode, PivotBoard, UserInteractionContext


class DefaultAIService(AIServiceProtocol):
    """Application-level AI orchestrator. Dispatches requests to external infrastructure."""

    def __init__(self, api_key: str | None = None, model: str = "google/gemini-2.5-flash") -> None:
        self.api_key = api_key
        self.model = model

    def generate_summary(self, content: str) -> str:
        if not self.api_key:
            return f"Generated Summary of: {content[:20]}..."

        # Simulated OpenRouter integration

        return f"Generated Summary of: {content[:20]}..."

    def generate_question(self, node: DocumentNode) -> str:
        if not self.api_key:
            return f"What is the key point of {node.title}?"

        # Real integration would make an HTTP request here using self.model
        return f"What is the key point of {node.title}?"

    def generate_mermaid_diagram(self, board: PivotBoard) -> str:
        return "graph TD;\n  A-->B;"

    def evaluate_answer(self, context: UserInteractionContext) -> tuple[bool, str]:
        if context.user_answer and "budget > 5000" in context.user_answer:
            return True, "Correct!"
        return False, "Incorrect."
