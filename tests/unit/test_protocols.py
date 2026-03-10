from src.domain_models import (
    ContentNode,
    DocumentRepository,
    IdentityNode,
)


class MockDocumentRepository:
    """Mock implementation of DocumentRepository to test Protocol conformance."""

    def __init__(self) -> None:
        self.identities: dict[str, IdentityNode] = {}
        self.contents: dict[str, ContentNode] = {}

    def save_identity_node(self, node: IdentityNode) -> None:
        self.identities[node.id] = node

    def get_identity_node(self, node_id: str) -> IdentityNode | None:
        return self.identities.get(node_id)

    def save_content_node(self, node: ContentNode) -> None:
        self.contents[node.id] = node

    def get_content_node(self, node_id: str) -> ContentNode | None:
        return self.contents.get(node_id)


class FaultyUserRepository:
    """Intentionally faulty mock to show type checker would fail.

    `get_user_state` is missing `user_id` parameter, and `save_user_state` is missing.
    """

    def get_user_state(self) -> dict[str, str]:
        return {}


def test_document_repository_protocol() -> None:
    # A properly implemented mock can be assigned to the protocol variable.
    repo: DocumentRepository = MockDocumentRepository()
    assert repo is not None
