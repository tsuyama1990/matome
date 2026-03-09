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


def test_default_ai_service_generate_summary() -> None:
    ai = DefaultAIService()
    summary = ai.generate_summary("This is a long test content string.")
    assert summary.startswith("Generated Summary of:")


def test_default_ai_service_generate_question() -> None:
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
    question = ai.generate_question(node)
    assert question == "What is the key point of Test Title?"


def test_default_ai_service_generate_mermaid_diagram() -> None:
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
    diagram = ai.generate_mermaid_diagram(board)
    assert "graph TD" in diagram


def test_default_ai_service_evaluate_answer() -> None:
    ai = DefaultAIService()
    context = UserInteractionContext(
        node_id="test1",
        status=NodeStatus.LOCKED,
        question_asked="What?",
        user_answer="budget > 5000",
        feedback=None,
        hints_used=0,
    )
    success, feedback = ai.evaluate_answer(context)
    assert success is True
    assert feedback == "Correct!"

    context.user_answer = "wrong answer"
    success, feedback = ai.evaluate_answer(context)
    assert success is False
    assert feedback == "Incorrect."
