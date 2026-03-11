from typing import Any, Protocol

from src.domain_models import KnowledgeNode, PivotResponse, SemanticChunk, SummaryTree


class LLMError(Exception):
    """Exception raised when an LLM invocation fails."""


class ProcessingError(Exception):
    """Exception raised when document processing fails."""


class GraphError(Exception):
    """Exception raised when knowledge graph operations fail."""


class ActiveLearningError(Exception):
    """Exception raised when active learning evaluation or question generation fails."""


class LLMProtocol(Protocol):
    """Protocol for LLM interactions like OpenRouterGateway."""

    def invoke(self, prompt: str, **kwargs: Any) -> str:
        """Invokes the LLM with a prompt and returns the string response.

        Raises:
            LLMError: If the underlying model API fails or returns invalid responses.
        """
        ...


class DocumentProcessingService(Protocol):
    """Protocol for the DocumentProcessingService."""

    def process(self, file_path: str) -> list[SemanticChunk]:
        """Processes a file and returns semantic chunks.

        Raises:
            ProcessingError: If the document cannot be read, parsed, or chunked securely.
            ValueError: If the file_path is fundamentally invalid or violates security constraints.
        """
        ...


class KnowledgeGraphService(Protocol):
    """Protocol for the KnowledgeGraphService."""

    def generate_raptor_tree(self, chunks: list[SemanticChunk]) -> SummaryTree:
        """Builds a hierarchical tree from semantic chunks.

        Raises:
            GraphError: If the graph generation algorithms fail or the input chunks are invalid.
        """
        ...

    def pivot_kj(self, tree: SummaryTree, axis: str) -> PivotResponse:
        """Rearranges the tree based on an axis.

        Raises:
            GraphError: If the Pivot KJ engine fails to restructure the knowledge or generate artifacts.
        """
        ...


class ActiveLearningService(Protocol):
    """Protocol for the ActiveLearningService."""

    def evaluate_answer(self, node: KnowledgeNode, answer: str) -> bool:
        """Evaluates an answer and updates the node state.

        Raises:
            ActiveLearningError: If the evaluation engine fails or the node state cannot be transitioned safely.
        """
        ...

    def generate_question(self, node: KnowledgeNode) -> str:
        """Generates a question for a locked node.

        Raises:
            ActiveLearningError: If prompt generation fails.
        """
        ...
