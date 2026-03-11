from typing import Any, Protocol

from src.domain_models import KnowledgeNode, PivotResponse, SemanticChunk, SummaryTree


class LLMProtocol(Protocol):
    """Protocol for LLM interactions like OpenRouterGateway."""

    def invoke(self, prompt: str, **kwargs: Any) -> str:
        """Invokes the LLM with a prompt and returns the string response."""
        ...


class DocumentProcessingService(Protocol):
    """Protocol for the DocumentProcessingService."""

    def process(self, file_path: str) -> list[SemanticChunk]:
        """Processes a file and returns semantic chunks."""
        ...


class KnowledgeGraphService(Protocol):
    """Protocol for the KnowledgeGraphService."""

    def generate_raptor_tree(self, chunks: list[SemanticChunk]) -> SummaryTree:
        """Builds a hierarchical tree from semantic chunks."""
        ...

    def pivot_kj(self, tree: SummaryTree, axis: str) -> PivotResponse:
        """Rearranges the tree based on an axis."""
        ...


class ActiveLearningService(Protocol):
    """Protocol for the ActiveLearningService."""

    def evaluate_answer(self, node: KnowledgeNode, answer: str) -> bool:
        """Evaluates an answer and updates the node state."""
        ...

    def generate_question(self, node: KnowledgeNode) -> str:
        """Generates a question for a locked node."""
        ...
