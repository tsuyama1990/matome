from src.domain_models import DocumentNode
from src.interfaces.protocols import AIServiceProtocol


class MockAIService(AIServiceProtocol):
    """Mock implementation of the AIServiceProtocol for testing and isolated pipelines."""

    def generate_summary(self, content: str) -> str:
        return f"CoD Summary of: {content[:20]}..."

    def generate_question(self, node: DocumentNode) -> str:
        return f"What is the key point of {node.title}?"
