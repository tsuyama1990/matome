from typing import Any

from src.domain_models import (
    ContentNode,
    DocumentRepository,
    IdentityNode,
)


class MockDocumentRepository:
    def begin(self) -> None:
        pass

    def commit(self) -> None:
        pass

    def rollback(self) -> None:
        pass

    def save_identity(self, node: IdentityNode) -> None:
        pass

    def save_content(self, node: ContentNode) -> None:
        pass

    def get_identity(self, node_id: str) -> IdentityNode | None:
        return None

    def get_content(self, node_id: str) -> ContentNode | None:
        return None

    def get_children(self, parent_id: str) -> list[IdentityNode]:
        return []

    def query_nodes(self, filters: dict[str, Any]) -> list[IdentityNode]:
        return []


def test_mock_document_repository_implements_protocol() -> None:
    repo: DocumentRepository = MockDocumentRepository()
    assert hasattr(repo, "save_identity")
    assert hasattr(repo, "save_content")
    assert hasattr(repo, "get_identity")
    assert hasattr(repo, "get_content")
    assert hasattr(repo, "get_children")
