import pytest
from pydantic import ValidationError

from src.domain_models import (
    AIProcessingMetadata,
    BestPracticeData,
    DocumentContent,
    DocumentNode,
    NodeMetadata,
    NodeStatus,
    PivotAxis,
    PivotBoard,
    PivotBoardViewNode,
    SummaryNode,
    UserInteractionContext,
    WisdomData,
)


def test_document_node_valid() -> None:
    node = DocumentNode(
        id="node1",
        parent_id=None,
        title="Test Node",
        content=DocumentContent(summary=None, text=None),
        status=NodeStatus.LOCKED,
        metadata=NodeMetadata(
            source=None,
            author="test",
            category=None,
            time_axis=None,
            best_practices=[BestPracticeData(content="Test best practice")],
            wisdom_data=[WisdomData(content="Test wisdom")],
        ),
        ai_metadata=AIProcessingMetadata(
            chunk_id=None, chunk_index=None, entity_metadata={}, hierarchical_tree={}
        ),
    )
    assert node.id == "node1"
    assert node.title == "Test Node"
    assert node.status == NodeStatus.LOCKED
    assert node.metadata.author == "test"
    assert len(node.metadata.best_practices) == 1
    assert node.metadata.best_practices[0].content == "Test best practice"


def test_document_node_invalid_extra() -> None:
    with pytest.raises(ValidationError):
        DocumentNode(
            id="node1",
            parent_id=None,
            title="Test Node",
            content=DocumentContent(summary=None, text=None),
            metadata=NodeMetadata(source=None, author="test", category=None, time_axis=None),
            extra_field="Not allowed",  # type: ignore
        )


def test_user_interaction_context_valid() -> None:
    ctx = UserInteractionContext(
        node_id="node1",
        status=NodeStatus.LOCKED,
        question_asked=None,
        user_answer=None,
        feedback=None,
        hints_used=0,
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
            hints_used=-1,
        )


def test_summary_node_valid() -> None:
    summary_node = SummaryNode(
        id=123,
        title="Summary Title",
        summary="This is a summary",
        children_indices=[1, "child_2"],
    )
    assert summary_node.id == 123
    assert len(summary_node.children_indices) == 2
    assert summary_node.children_indices[1] == "child_2"


def test_pivot_board_valid() -> None:
    board = PivotBoard(
        id="board1",
        original_root_id="root1",
        axis=PivotAxis.ACTOR_STATE,
        custom_axis_description=None,
        nodes=[
            PivotBoardViewNode(node_id="node1", x_position=0.5, y_position=0.5, cluster_id=None)
        ],
    )
    assert board.id == "board1"
    assert board.axis == PivotAxis.ACTOR_STATE
    assert len(board.nodes) == 1
    assert board.nodes[0].x_position == 0.5
