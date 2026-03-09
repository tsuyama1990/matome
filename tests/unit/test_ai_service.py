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
from src.domain_models.interfaces import AIServiceError


def test_default_ai_service_missing_key_init() -> None:
    from src.config import Settings

    with pytest.raises(ValueError, match="A valid API Key is required"):
        DefaultAIService(settings=Settings(openrouter_api_key=None))


def test_default_ai_service_invalid_key_length() -> None:
    from pydantic import SecretStr, ValidationError

    from src.config import Settings

    with pytest.raises(ValidationError, match="API Key must be at least 30 characters long"):
        DefaultAIService(settings=Settings(openrouter_api_key=SecretStr("123")))


def test_default_ai_service_invalid_key_format() -> None:
    from pydantic import SecretStr, ValidationError

    from src.config import Settings

    with pytest.raises(ValidationError, match="API Key format is invalid"):
        DefaultAIService(
            settings=Settings(
                openrouter_api_key=SecretStr("invalid_format_key_with_spaces and_tabs")
            )
        )


def test_default_ai_service_calls_generate_summary_valid() -> None:
    import os

    from src.config import Settings

    os.environ["OPENROUTER_API_KEY"] = "sk-or-v1-validkey12345678901234567890"
    try:
        ai = DefaultAIService(settings=Settings())
        with pytest.raises(AIServiceError):
            # Without a mocked network interface, this should raise the AIServiceError (either HTTP/Connection)
            ai.generate_summary("test content")
    finally:
        del os.environ["OPENROUTER_API_KEY"]


def test_default_ai_service_calls_generate_question_valid() -> None:
    import os

    from src.config import Settings

    os.environ["OPENROUTER_API_KEY"] = "sk-or-v1-validkey12345678901234567890"
    try:
        ai = DefaultAIService(settings=Settings())
    finally:
        del os.environ["OPENROUTER_API_KEY"]
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
    with pytest.raises(AIServiceError):
        ai.generate_question(node)


def test_default_ai_service_calls_generate_mermaid_valid() -> None:
    import os

    from src.config import Settings

    os.environ["OPENROUTER_API_KEY"] = "sk-or-v1-validkey12345678901234567890"
    try:
        ai = DefaultAIService(settings=Settings())
    finally:
        del os.environ["OPENROUTER_API_KEY"]
    board = PivotBoard(
        id="board_1",
        original_root_id="root_1",
        axis=PivotAxis.ACTOR_STATE,
        custom_axis_description=None,
        nodes=[
            PivotBoardViewNode(node_id="test1", x_position=0.1, y_position=0.2, cluster_id=None)
        ],
    )
    with pytest.raises(AIServiceError):
        ai.generate_mermaid_diagram(board)


def test_default_ai_service_calls_evaluate_answer_valid() -> None:
    import os

    from src.config import Settings

    os.environ["OPENROUTER_API_KEY"] = "sk-or-v1-validkey12345678901234567890"
    try:
        ai = DefaultAIService(settings=Settings())
    finally:
        del os.environ["OPENROUTER_API_KEY"]
    context = UserInteractionContext(
        node_id="test1",
        status=NodeStatus.LOCKED,
        question_asked="What?",
        user_answer="budget > 5000",
        feedback=None,
        hints_used=0,
    )
    with pytest.raises(AIServiceError):
        ai.evaluate_answer(context)
