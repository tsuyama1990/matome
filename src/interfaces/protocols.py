from typing import Protocol

from src.domain_models import DocumentNode, PivotBoard, UserInteractionContext


class DocumentRepository(Protocol):
    def save_node(self, node: DocumentNode) -> None:
        ...

    def get_node(self, node_id: str) -> DocumentNode | None:
        ...

    def get_children(self, parent_id: str) -> list[DocumentNode]:
        ...

class UserInteractionRepository(Protocol):
    def save_context(self, context: UserInteractionContext) -> None:
        ...

    def get_context(self, node_id: str) -> UserInteractionContext | None:
        ...

class PivotBoardRepository(Protocol):
    def save_board(self, board: PivotBoard) -> None:
        ...

    def get_board(self, board_id: str) -> PivotBoard | None:
        ...
