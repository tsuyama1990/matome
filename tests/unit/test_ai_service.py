import pytest

from src.application.ai import DefaultAIService
from src.domain_models import (
    AIProcessingMetadata,
    DocumentContent,
    DocumentNode,
    NodeMetadata,
    NodeStatus,
    PivotAxis,
    PivotBoard,
    PivotBoardViewNode,
    UserInteractionContext,
)


def test_default_ai_service_generate_summary_missing_key() -> None:
    ai = DefaultAIService()
    with pytest.raises(NotImplementedError):
        ai.generate_summary("This is a long test content string.")


def test_default_ai_service_generate_question_missing_key() -> None:
    ai = DefaultAIService()
    node = DocumentNode(
        id="test1",
        parent_id=None,
        title="Test Title",
        content=DocumentContent(summary=None, text=None),
        status=NodeStatus.LOCKED,
        metadata=NodeMetadata(source=None, author=None, category=None, time_axis=None),
        ai_metadata=AIProcessingMetadata(
            chunk_id=None, chunk_index=None, entity_metadata={}, hierarchical_tree={}
        ),
    )
    with pytest.raises(NotImplementedError):
        ai.generate_question(node)

def test_default_ai_service_generate_mermaid_diagram_missing_key() -> None:
    ai = DefaultAIService()
    board = PivotBoard(
        id="board_1",
        original_root_id="root_1",
        axis=PivotAxis.ACTOR_STATE,
        custom_axis_description=None,
        nodes=[
            PivotBoardViewNode(node_id="test1", x_position=0.1, y_position=0.2, cluster_id=None)
        ],
    )
    with pytest.raises(NotImplementedError):
        ai.generate_mermaid_diagram(board)

def test_default_ai_service_evaluate_answer_missing_key() -> None:
    ai = DefaultAIService()
    context = UserInteractionContext(
        node_id="test1",
        status=NodeStatus.LOCKED,
        question_asked="What?",
        user_answer="budget > 5000",
        feedback=None,
        hints_used=0,
    )
    with pytest.raises(NotImplementedError):
        ai.evaluate_answer(context)
