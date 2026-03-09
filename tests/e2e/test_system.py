from main import AppConfig, Application, MockAIService
from src.domain_models import (
    DocumentNode,
    NodeMetadata,
    NodeStatus,
    PivotAxis,
    PivotBoard,
    PivotBoardNode,
)
from src.infrastructure import InMemoryDocumentRepository
from src.interfaces import DocumentRepository


def test_e2e_document_ingestion_pipeline() -> None:
    """
    Tests the actual flow of creating and persisting multiple document nodes in a hierarchy.
    """
    repo: DocumentRepository = InMemoryDocumentRepository()

    # 1. Simulate document parsing into root and child nodes
    root_node = DocumentNode(
        id="doc_root",
        parent_id=None,
        title="Business Strategy 2024",
        summary="Overview of corporate goals",
        content=None,
        status=NodeStatus.UNLOCKED,
        metadata=NodeMetadata(source="upload", author="CEO", category=None, time_axis=None)
    )

    child_node = DocumentNode(
        id="doc_child_1",
        parent_id="doc_root",
        title="Q1 Objectives",
        summary="Detailed Q1 OKRs",
        content="Increase revenue by 20%...",
        status=NodeStatus.LOCKED,
        metadata=NodeMetadata(source=None, author=None, category=None, time_axis="Q1")
    )

    root_node.children_ids.append(child_node.id)

    # 2. Persist to DB
    repo.save_nodes([root_node, child_node])

    # 3. Verify retrieval and relationships
    retrieved_root = repo.get_node("doc_root")
    assert retrieved_root is not None
    assert retrieved_root.title == "Business Strategy 2024"

    children = repo.get_children("doc_root")
    assert len(children) == 1
    assert children[0].id == "doc_child_1"

def test_e2e_pivot_kj_pipeline() -> None:
    """
    Tests the creation of a multidimensional layout (PivotBoard) referencing actual nodes.
    """
    board = PivotBoard(
        id="board_strategy",
        original_root_id="doc_root",
        axis=PivotAxis.TIME,
        custom_axis_description=None,
        nodes=[
            PivotBoardNode(
                node_id="doc_child_1",
                x_position=0.25,
                y_position=0.75,
                cluster_id="q1_cluster"
            )
        ],
        mermaid_diagram="graph TD; doc_child_1-->goal;"
    )

    assert board.axis == PivotAxis.TIME
    assert len(board.nodes) == 1
    assert board.nodes[0].x_position == 0.25



def test_e2e_application_pipeline() -> None:
    """
    Tests the main application pipeline including ingestion and AI processing orchestration.
    """
    repo = InMemoryDocumentRepository()
    ai = MockAIService()
    config = AppConfig(mode="test")
    app = Application(config=config, doc_repo=repo, ai_service=ai)

    # Run the pipeline
    app.start()

    # Verify the results in the repository
    nodes = [repo.get_node("root_doc_1")] # Since it's saved as root (parent_id=None)
    assert len(nodes) == 1
    root = nodes[0]

    assert root is not None
    assert root.id == "root_doc_1"
    assert root.summary is not None
    assert "CoD Summary of: " in root.summary
    assert root.metadata.category == "business"
