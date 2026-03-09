from collections.abc import Callable, Iterator
from typing import Any, Protocol

from .analysis import PivotBoard
from .manifest import DocumentNode, UserInteractionContext


class DocumentRepository(Protocol):
    """Protocol for combining Read, Write, Query, and Transaction operations."""

    def begin(self) -> None:
        """Starts a new transaction. Should raise RepositoryError on failure."""
        ...

    def commit(self) -> None:
        """Commits the active transaction. Should raise RepositoryError on failure."""
        ...

    def rollback(self) -> None:
        """Rolls back the active transaction. Should raise RepositoryError on failure."""
        ...

    def get_node(self, node_id: str) -> DocumentNode | None:
        """Retrieves a node by its ID. Raises RepositoryError on DB failure."""
        ...

    def get_children(self, parent_id: str) -> list[DocumentNode]:
        """Retrieves all children of a given parent node ID. Raises RepositoryError on DB failure."""
        ...

    def save_node(self, node: DocumentNode) -> None:
        """Saves or updates a single node. Should be within a transaction. Raises RepositoryError on failure."""
        ...

    def save_nodes(self, nodes: list[DocumentNode]) -> None:
        """Saves or updates multiple nodes. Should be within a transaction. Raises RepositoryError on failure."""
        ...

    def query_nodes(self, filters: dict[str, Any]) -> list[DocumentNode]:
        """Queries nodes based on provided filters. Raises RepositoryError on failure."""
        ...


class AIServiceProtocol(Protocol):
    def generate_summary(self, content: str) -> str: ...
    def generate_question(self, node: DocumentNode) -> str: ...
    def generate_mermaid_diagram(self, board: PivotBoard) -> str: ...
    def evaluate_answer(self, context: UserInteractionContext) -> tuple[bool, str]: ...


class TextSplitterProtocol(Protocol):
    """Protocol for splitting text into smaller chunks."""

    def split_text(self, text: str) -> list[str]: ...
    def split_document(self, file_path: str) -> Iterator[str]: ...


class EntityExtractorProtocol(Protocol):
    """Protocol for extracting entities from an iterator of text chunks."""

    def extract_entities(self, chunks: Iterator[str] | list[str]) -> dict[str, str]: ...


class ClusteringServiceProtocol(Protocol):
    """Protocol for clustering chunks and returning metadata."""

    def cluster_chunks(
        self, chunks: Iterator[str] | list[str], max_clusters: int
    ) -> dict[str, str]: ...


class HTTPClientProtocol(Protocol):
    """Protocol for sending HTTP requests."""

    def post(
        self, url: str, json: dict[str, Any], headers: dict[str, str], timeout: int
    ) -> dict[str, Any]: ...


class RetryPolicyProtocol(Protocol):
    """Protocol for defining execution retry policies."""

    def execute(self, func: Callable[..., Any]) -> Any: ...
