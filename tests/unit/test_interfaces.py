from typing import Any

from src.domain_models import (
    DocumentNode,
    PivotBoard,
    UserInteractionContext,
)
from src.interfaces import DocumentRepository, PivotBoardRepository, UserInteractionRepository


class MockDocumentRepository:
    def save_node(self, node: DocumentNode) -> None:
        pass

    def save_nodes(self, nodes: list[DocumentNode]) -> None:
        pass

    def get_node(self, node_id: str) -> DocumentNode | None:
        return None

    def get_children(self, parent_id: str) -> list[DocumentNode]:
        return []

    def query_nodes(self, filters: dict[str, Any]) -> list[DocumentNode]:
        return []

class MockUserInteractionRepository:
    def save_context(self, context: UserInteractionContext) -> None:
        pass

    def get_context(self, node_id: str) -> UserInteractionContext | None:
        return None

class MockPivotBoardRepository:
    def save_board(self, board: PivotBoard) -> None:
        pass

    def get_board(self, board_id: str) -> PivotBoard | None:
        return None

def test_mock_document_repository_implements_protocol() -> None:
    repo: DocumentRepository = MockDocumentRepository()
    assert hasattr(repo, "save_node")
    assert hasattr(repo, "save_nodes")
    assert hasattr(repo, "get_node")
    assert hasattr(repo, "get_children")
    assert hasattr(repo, "query_nodes")

def test_mock_user_interaction_repository_implements_protocol() -> None:
    repo: UserInteractionRepository = MockUserInteractionRepository()
    assert hasattr(repo, "save_context")
    assert hasattr(repo, "get_context")

def test_mock_pivot_board_repository_implements_protocol() -> None:
    repo: PivotBoardRepository = MockPivotBoardRepository()
    assert hasattr(repo, "save_board")
    assert hasattr(repo, "get_board")
