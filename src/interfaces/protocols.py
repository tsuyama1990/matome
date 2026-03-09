from typing import Any, Protocol

from src.domain_models import DocumentNode, PivotBoard, UserInteractionContext


class RepositoryError(Exception):
    """Base exception for all repository-related errors."""

class Transactional(Protocol):
    """Protocol for transaction management."""
    def begin(self) -> None:
        ...

    def commit(self) -> None:
        ...

    def rollback(self) -> None:
        ...

class DocumentRepository(Protocol):
    def save_node(self, node: DocumentNode) -> None:
        """Saves a DocumentNode. Raises RepositoryError on failure."""
        ...

    def save_nodes(self, nodes: list[DocumentNode]) -> None:
        """Saves a batch of DocumentNodes. Raises RepositoryError on failure."""
        ...

    def get_node(self, node_id: str) -> DocumentNode | None:
        """Retrieves a DocumentNode by its ID. Raises RepositoryError on DB errors."""
        ...

    def get_children(self, parent_id: str) -> list[DocumentNode]:
        """Retrieves child DocumentNodes. Raises RepositoryError on DB errors."""
        ...

    def query_nodes(self, filters: dict[str, Any]) -> list[DocumentNode]:
        """Queries DocumentNodes based on metadata/status filters. Raises RepositoryError on failure."""
        ...

class UserInteractionRepository(Protocol):
    def save_context(self, context: UserInteractionContext) -> None:
        """Saves UserInteractionContext. Raises RepositoryError on failure."""
        ...

    def get_context(self, node_id: str) -> UserInteractionContext | None:
        """Retrieves UserInteractionContext. Raises RepositoryError on DB errors."""
        ...

class PivotBoardRepository(Protocol):
    def save_board(self, board: PivotBoard) -> None:
        """Saves PivotBoard. Raises RepositoryError on failure."""
        ...

    def get_board(self, board_id: str) -> PivotBoard | None:
        """Retrieves PivotBoard. Raises RepositoryError on DB errors."""
        ...

class AIMockService(Protocol):
    def generate_summary(self, content: str) -> str:
        ...

    def generate_question(self, node: DocumentNode) -> str:
        ...
