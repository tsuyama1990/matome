from src.domain_models import DocumentNode, NodeStatus, PivotAxis, PivotBoard


def test_e2e_document_ingestion_skeleton() -> None:
    """
    Simulates the E2E flow of uploading a document and creating nodes.
    Currently acts as a skeleton for future real backend integration.
    """
    root_node = DocumentNode(
        id="doc_1",
        parent_id=None,
        title="Root Document",
        summary=None,
        content=None,
        status=NodeStatus.UNLOCKED,
        metadata={"source": "upload"}
    )
    assert root_node.id == "doc_1"
    assert root_node.status == NodeStatus.UNLOCKED

def test_e2e_pivot_kj_skeleton() -> None:
    """
    Simulates the E2E flow of user selecting a pivot axis and getting a new board.
    """
    board = PivotBoard(
        id="board_1",
        original_root_id="doc_1",
        axis=PivotAxis.TIME,
        custom_axis_description=None,
        nodes=[],
        mermaid_diagram=None
    )
    assert board.axis == PivotAxis.TIME
