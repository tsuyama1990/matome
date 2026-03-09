from src.domain_models import (
    ContentNode,
    IdentityNode,
    NodeStatus,
)
from src.infrastructure.repository import InMemoryDocumentRepository


def create_mock_identity(
    node_id: str, parent_id: str | None = None, status: NodeStatus = NodeStatus.LOCKED
) -> IdentityNode:
    return IdentityNode(
        id=node_id,
        parent_id=parent_id,
        title=node_id,
        status=status,
    )


def create_mock_content(node_id: str) -> ContentNode:
    return ContentNode(node_id=node_id, summary=None, text=None)


def test_in_memory_repo_save_and_get() -> None:
    repo = InMemoryDocumentRepository()
    repo.begin()

    id1 = create_mock_identity("n1")
    content1 = create_mock_content("n1")
    id2 = create_mock_identity("n2")
    content2 = create_mock_content("n2")

    repo.save_identity(id1)
    repo.save_content(content1)
    repo.save_identity(id2)
    repo.save_content(content2)
    repo.commit()

    assert repo.get_identity("n1") == id1
    assert repo.get_content("n1") == content1
    assert repo.get_identity("n2") == id2
    assert repo.get_content("n2") == content2


def test_in_memory_repo_get_children() -> None:
    repo = InMemoryDocumentRepository()
    repo.begin()
    id1 = create_mock_identity("n1", parent_id="root")
    id2 = create_mock_identity("n2", parent_id="root")
    id3 = create_mock_identity("n3", parent_id="other")

    repo.save_identity(id1)
    repo.save_identity(id2)
    repo.save_identity(id3)
    repo.commit()

    children = repo.get_children("root")
    assert len(children) == 2
    assert id1 in children
    assert id2 in children


def test_in_memory_query_service() -> None:
    repo = InMemoryDocumentRepository()
    repo.begin()

    id1 = create_mock_identity("n1", status=NodeStatus.LOCKED)
    id2 = create_mock_identity("n2", status=NodeStatus.UNLOCKED)
    repo.save_identity(id1)
    repo.save_identity(id2)
    repo.commit()

    results = [node for node in repo._identities.values() if node.status == NodeStatus.UNLOCKED]
    assert len(results) == 1
    assert results[0].id == "n2"
