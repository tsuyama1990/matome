from typing import Any

from src.domain_models import (
    DocumentNode,
    DocumentRepository,
)


class MockDocumentRepository:
    def begin(self) -> None:
        pass

    def commit(self) -> None:
        pass

    def rollback(self) -> None:
        pass

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


def test_mock_document_repository_implements_protocol() -> None:
    repo: DocumentRepository = MockDocumentRepository()
    assert hasattr(repo, "save_node")
    assert hasattr(repo, "save_nodes")
    assert hasattr(repo, "get_node")
    assert hasattr(repo, "get_children")
    assert hasattr(repo, "query_nodes")
