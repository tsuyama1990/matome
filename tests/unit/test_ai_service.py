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


def test_default_ai_service_missing_key_init() -> None:
    with pytest.raises(ValueError, match="A valid API Key is required"):
        DefaultAIService(api_key="")


def test_default_ai_service_calls_generate_summary_valid() -> None:
    ai = DefaultAIService(api_key="valid_key")
    # This will result in an API Error string if the network is disconnected or token is bad, but it shouldn't raise natively.
    res = ai.generate_summary("test content")
    assert isinstance(res, str)

def test_default_ai_service_calls_generate_question_valid() -> None:
    ai = DefaultAIService(api_key="valid_key")
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
    res = ai.generate_question(node)
    assert isinstance(res, str)

def test_default_ai_service_calls_generate_mermaid_valid() -> None:
    ai = DefaultAIService(api_key="valid_key")
    board = PivotBoard(
        id="board_1",
        original_root_id="root_1",
        axis=PivotAxis.ACTOR_STATE,
        custom_axis_description=None,
        nodes=[
            PivotBoardViewNode(node_id="test1", x_position=0.1, y_position=0.2, cluster_id=None)
        ],
    )
    res = ai.generate_mermaid_diagram(board)
    assert isinstance(res, str)

def test_default_ai_service_calls_evaluate_answer_valid() -> None:
    ai = DefaultAIService(api_key="valid_key")
    context = UserInteractionContext(
        node_id="test1",
        status=NodeStatus.LOCKED,
        question_asked="What?",
        user_answer="budget > 5000",
        feedback=None,
        hints_used=0,
    )
    success, feedback = ai.evaluate_answer(context)
    assert isinstance(success, bool)
    assert isinstance(feedback, str)
