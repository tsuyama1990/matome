from typing import Any, Protocol

from .analysis import PivotBoard
from .manifest import DocumentNode, UserInteractionContext


class RepositoryError(Exception):
    """Base exception for all repository-related errors."""


class AIServiceError(Exception):
    """Base exception for external AI service failures."""


class Transactional(Protocol):
    """Protocol for transaction management."""

    def begin(self) -> None: ...
    def commit(self) -> None: ...
    def rollback(self) -> None: ...


class DocumentReader(Protocol):
    def get_node(self, node_id: str) -> DocumentNode | None: ...
    def get_children(self, parent_id: str) -> list[DocumentNode]: ...


class DocumentWriter(Protocol):
    def save_node(self, node: DocumentNode) -> None: ...
    def save_nodes(self, nodes: list[DocumentNode]) -> None: ...


class DocumentQueryService(Protocol):
    """Protocol for complex query operations over documents."""

    def query_nodes(self, filters: dict[str, Any]) -> list[DocumentNode]: ...


class DocumentRepository(
    DocumentReader, DocumentWriter, Transactional, DocumentQueryService, Protocol
):
    """Aggregate protocol combining Read, Write, Query, and Transaction operations."""


class UserInteractionRepository(Protocol):
    def save_context(self, context: UserInteractionContext) -> None: ...
    def get_context(self, node_id: str) -> UserInteractionContext | None: ...


class PivotBoardRepository(Protocol):
    def save_board(self, board: PivotBoard) -> None: ...
    def get_board(self, board_id: str) -> PivotBoard | None: ...


class AIServiceProtocol(Protocol):
    def generate_summary(self, content: str) -> str: ...
    def generate_question(self, node: DocumentNode) -> str: ...
    def generate_mermaid_diagram(self, board: PivotBoard) -> str: ...
    def evaluate_answer(self, context: UserInteractionContext) -> tuple[bool, str]: ...
