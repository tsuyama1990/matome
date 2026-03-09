import pytest
from pydantic import ValidationError

from src.domain_models import (
    DocumentNode,
    NodeStatus,
    PivotAxis,
    PivotBoard,
    PivotBoardNode,
    UserInteractionContext,
)


def test_document_node_valid() -> None:
    node = DocumentNode(
        id="node1",
        parent_id=None,
        title="Test Node",
        summary=None,
        content=None,
        status=NodeStatus.LOCKED,
        metadata={"author": "test"}
    )
    assert node.id == "node1"
    assert node.title == "Test Node"
    assert node.status == NodeStatus.LOCKED
    assert node.metadata == {"author": "test"}

def test_document_node_invalid_extra() -> None:
    with pytest.raises(ValidationError):
        DocumentNode(
            id="node1",
            parent_id=None,
            title="Test Node",
            summary=None,
            content=None,
            extra_field="Not allowed" # type: ignore
        )

def test_user_interaction_context_valid() -> None:
    ctx = UserInteractionContext(
        node_id="node1",
        status=NodeStatus.LOCKED,
        question_asked=None,
        user_answer=None,
        feedback=None,
        hints_used=0
    )
    assert ctx.node_id == "node1"
    assert ctx.status == NodeStatus.LOCKED
    assert ctx.hints_used == 0

def test_user_interaction_context_invalid_hints() -> None:
    with pytest.raises(ValidationError):
        UserInteractionContext(
            node_id="node1",
            status=NodeStatus.LOCKED,
            question_asked=None,
            user_answer=None,
            feedback=None,
            hints_used=-1
        )

def test_pivot_board_valid() -> None:
    board = PivotBoard(
        id="board1",
        original_root_id="root1",
        axis=PivotAxis.ACTOR_STATE,
        custom_axis_description=None,
        nodes=[
            PivotBoardNode(node_id="node1", x_position=10.0, y_position=20.0, cluster_id=None)
        ],
        mermaid_diagram=None
    )
    assert board.id == "board1"
    assert board.axis == PivotAxis.ACTOR_STATE
    assert len(board.nodes) == 1
    assert board.nodes[0].x_position == 10.0
