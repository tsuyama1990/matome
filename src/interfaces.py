from collections.abc import Iterator
from typing import Any, Protocol

from src.domain_models import GraphState, KnowledgeNode, SemanticChunk


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

    def invoke(self, prompt: str, timeout: int = 30, retries: int = 3, **kwargs: Any) -> str:
        """Invokes the LLM with a prompt, timeout, and retry logic.

        Raises:
            LLMError: If the underlying model API fails or returns invalid responses.
        """
        ...


class VectorDBProtocol(Protocol):
    """Protocol for Vector Database interactions."""

    def store(self, chunks: list[SemanticChunk]) -> None:
        """Stores a list of semantic chunks in the vector database.

        Raises:
            ProcessingError: If storage operation fails.
        """
        ...

    def search(self, query: str, top_k: int = 5) -> list[SemanticChunk]:
        """Searches for chunks similar to the query.

        Raises:
            ProcessingError: If search operation fails.
        """
        ...


class DocumentProcessingService(Protocol):
    """Protocol for the DocumentProcessingService executing within a LangGraph state machine."""

    def process(self, state: GraphState) -> Iterator[GraphState]:
        """Processes a file referenced in state and yields incremental state updates to avoid memory exhaustion.

        Raises:
            ProcessingError: If the document cannot be read, parsed, or chunked securely.
            ValueError: If the file_path is fundamentally invalid or violates security constraints.
        """
        ...

    def process_stream(self, file_path: str, chunk_size: int = 1000) -> Iterator[SemanticChunk]:
        """Streams a file processing to reduce memory overhead."""
        ...


class KnowledgeGraphService(Protocol):
    """Protocol for the KnowledgeGraphService executing within a LangGraph state machine."""

    def generate_raptor_tree(self, state: GraphState) -> GraphState:
        """Builds a hierarchical tree from semantic chunks in state and updates state.tree.

        Raises:
            GraphError: If the graph generation algorithms fail or the input chunks are invalid.
        """
        ...

    def generate_raptor_tree_batch(self, state: GraphState, batch_size: int = 100) -> GraphState:
        """Processes massive chunk lists in batches safely."""
        ...

    def pivot_kj(self, state: GraphState) -> GraphState:
        """Rearranges the tree based on state.pivot_axis and updates state.pivot_response.

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

    def generate_question(self, node: KnowledgeNode, difficulty: str = "normal") -> str:
        """Generates an adaptive question for a locked node.

        Raises:
            ActiveLearningError: If prompt generation fails.
        """
        ...

    def track_progress(self, user_id: str, node_id: str, success: bool) -> None:
        """Records progress analytics."""
        ...

    def get_feedback(self, node: KnowledgeNode, answer: str) -> str:
        """Generates constructive, targeted feedback."""
        ...
