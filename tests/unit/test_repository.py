from src.domain_models import (
    AIProcessingMetadata,
    DocumentContent,
    DocumentNode,
    NodeMetadata,
    NodeStatus,
)
from src.infrastructure.repository import InMemoryDocumentQueryService, InMemoryDocumentRepository


def create_mock_node(
    node_id: str, parent_id: str | None = None, status: NodeStatus = NodeStatus.LOCKED
) -> DocumentNode:
    return DocumentNode(
        id=node_id,
        parent_id=parent_id,
        title=node_id,
        content=DocumentContent(summary=None, text=None),
        status=status,
        metadata=NodeMetadata(source=None, author=None, category=None, time_axis=None),
        ai_metadata=AIProcessingMetadata(
            chunk_id=None, chunk_index=None, entity_metadata={}, hierarchical_tree={}
        ),
    )


def test_in_memory_repo_save_and_get() -> None:
    repo = InMemoryDocumentRepository()
    node1 = create_mock_node("n1")
    node2 = create_mock_node("n2")

    repo.save_nodes([node1, node2])
    assert repo.get_node("n1") == node1
    assert repo.get_node("n2") == node2


def test_in_memory_repo_get_children() -> None:
    repo = InMemoryDocumentRepository()
    node1 = create_mock_node("n1", parent_id="root")
    node2 = create_mock_node("n2", parent_id="root")
    node3 = create_mock_node("n3", parent_id="other")

    repo.save_nodes([node1, node2, node3])

    children = repo.get_children("root")
    assert len(children) == 2
    assert node1 in children
    assert node2 in children


def test_in_memory_query_service() -> None:
    repo = InMemoryDocumentRepository()
    qs = InMemoryDocumentQueryService(repo)

    node1 = create_mock_node("n1", status=NodeStatus.LOCKED)
    node2 = create_mock_node("n2", status=NodeStatus.UNLOCKED)
    repo.save_nodes([node1, node2])

    results = qs.query_nodes({"status": NodeStatus.UNLOCKED})
    assert len(results) == 1
    assert results[0].id == "n2"
