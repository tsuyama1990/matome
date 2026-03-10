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

    def get_api_key(self) -> Any: ...


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

    def get_identity(self, node_id: str) -> IdentityNode | None: ...

    def get_content(self, node_id: str) -> ContentNode | None: ...

    def get_children(self, parent_id: str) -> list[IdentityNode]: ...

    def save_identity(self, node: IdentityNode) -> None: ...

    def save_content(self, node: ContentNode) -> None: ...


class SummaryServiceProtocol(Protocol):
    def generate_summary(self, content: str) -> str: ...


class QuestionServiceProtocol(Protocol):
    def generate_question(self, identity: IdentityNode, content: ContentNode) -> str: ...


class DiagramServiceProtocol(Protocol):
    def generate_mermaid_diagram(self, board: PivotBoard) -> str: ...


class DocumentGenerationServiceProtocol(Protocol):
    def generate_markdown_requirements(self, board: PivotBoard) -> str: ...


class WebGroundingServiceProtocol(Protocol):
    def verify_web_grounding(self, content: str) -> str: ...


class EvaluationServiceProtocol(Protocol):
    def evaluate_answer(self, context: UserInteractionContext) -> tuple[bool, str]: ...


class AIServiceProtocol(
    SummaryServiceProtocol,
    QuestionServiceProtocol,
    DiagramServiceProtocol,
    DocumentGenerationServiceProtocol,
    WebGroundingServiceProtocol,
    EvaluationServiceProtocol,
    Protocol,
):
    """Aggregate protocol for backward compatibility or cases where all are needed."""


class SplitterStrategyProtocol(Protocol):
    """Protocol for the underlying strategy used to split text into list of chunks."""

    def split_text(self, text: str, chunk_size: int, chunk_overlap: int) -> list[str]: ...


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
        self,
        url: str,
        json: dict[str, Any],
        headers: dict[str, str],
        timeout: int,
        verify: bool | str = True,
        auth_token: Any | None = None,
    ) -> dict[str, Any]: ...


class AISecurityScannerProtocol(Protocol):
    """Protocol for securing AI inputs against prompt injection."""

    def sanitize(self, text: str | None) -> str: ...


class AICommunicationClientProtocol(Protocol):
    """Protocol for communicating with AI models."""

    def call_api(self, prompt: str, model: str | None = None) -> str: ...


class RetryPolicyProtocol(Protocol):
    """Protocol for defining execution retry policies."""

    def execute(self, func: Callable[..., Any]) -> Any: ...
