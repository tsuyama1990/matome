from collections.abc import Callable, Iterator
from typing import Any, Protocol

from .analysis import PivotBoard
from .manifest import ContentNode, IdentityNode, UserInteractionContext


class ConfigService(Protocol):
    """Protocol for fetching application configuration."""

    def get(self, key: str) -> Any: ...


class SecurityService(Protocol):
    """Protocol for security operations such as API key validation."""

    def validate_api_key(self, api_key: str) -> str: ...


class CredentialProviderProtocol(Protocol):
    """Protocol for securely providing sensitive credentials strictly at runtime without hoarding."""

    def get_api_key(self) -> str: ...


class TransactionManager(Protocol):
    """Protocol for handling transaction lifecycle operations."""

    def begin(self) -> None:
        """Starts a new transaction. Should raise RepositoryError on failure."""
        ...

    def commit(self) -> None:
        """Commits the active transaction. Should raise RepositoryError on failure."""
        ...

    def rollback(self) -> None:
        """Rolls back the active transaction. Should raise RepositoryError on failure."""
        ...


class DocumentRepository(Protocol):
    """Protocol for data persistence operations regarding decoupled nodes."""

    def get_identity(self, node_id: str) -> IdentityNode | None:
        ...

    def get_content(self, node_id: str) -> ContentNode | None:
        ...

    def get_children(self, parent_id: str) -> list[IdentityNode]:
        ...

    def save_identity(self, node: IdentityNode) -> None:
        ...

    def save_content(self, node: ContentNode) -> None:
        ...


class SummaryServiceProtocol(Protocol):
    def generate_summary(self, content: str) -> str: ...


class QuestionServiceProtocol(Protocol):
    def generate_question(self, identity: IdentityNode, content: ContentNode) -> str: ...


class DiagramServiceProtocol(Protocol):
    def generate_mermaid_diagram(self, board: PivotBoard) -> str: ...


class EvaluationServiceProtocol(Protocol):
    def evaluate_answer(self, context: UserInteractionContext) -> tuple[bool, str]: ...


class AIServiceProtocol(
    SummaryServiceProtocol,
    QuestionServiceProtocol,
    DiagramServiceProtocol,
    EvaluationServiceProtocol,
    Protocol,
):
    """Aggregate protocol for backward compatibility or cases where all are needed."""


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
