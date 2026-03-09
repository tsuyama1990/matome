from src.domain_models import AIServiceProtocol, DocumentNode


class DefaultAIService(AIServiceProtocol):
    """Production implementation of the AIServiceProtocol."""

    def generate_summary(self, content: str) -> str:
        # Currently a placeholder for actual LLM implementation
        return f"Generated Summary of: {content[:20]}..."

    def generate_question(self, node: DocumentNode) -> str:
        # Currently a placeholder for actual LLM implementation
        return f"What is the key point of {node.title}?"
