from src.domain_models import AIServiceProtocol, DocumentNode


class DefaultAIService(AIServiceProtocol):
    """Application-level AI orchestrator. Dispatches requests to external infrastructure."""

    def generate_summary(self, content: str) -> str:
        # In a real app, this would use a LangChain or OpenRouter client instance
        return f"Generated Summary of: {content[:20]}..."

    def generate_question(self, node: DocumentNode) -> str:
        return f"What is the key point of {node.title}?"
