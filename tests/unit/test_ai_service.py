
import pytest

from src.application.ai import DefaultAIService
from src.config import Settings
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
from src.domain_models.exceptions import AIServiceError


def _create_mock_settings(api_key: str | None = None) -> Settings:
    import os

    if api_key is not None:
        os.environ["OPENROUTER_API_KEY"] = api_key
    elif "OPENROUTER_API_KEY" in os.environ:
        del os.environ["OPENROUTER_API_KEY"]

    from pydantic import SecretStr

    try:
        # Pass dynamically resolved secret from environment to satisfy strict typings.
        api_key_str = os.environ.get("OPENROUTER_API_KEY", "")
        # Since pydantic validator catches invalid secrets, we can pass it directly
        return Settings(
            openrouter_api_key=SecretStr(api_key_str) if api_key_str else None, # type: ignore
            text_fast_model="google/gemini-2.5-flash",
            text_reasoning_model="deepseek/deepseek-reasoner",
            multimodal_model="openai/gpt-4o",
        )
    finally:
        if "OPENROUTER_API_KEY" in os.environ:
            del os.environ["OPENROUTER_API_KEY"]


def _create_service(api_key: str | None = None) -> DefaultAIService:
    from src.infrastructure.services import RequestsHTTPClient, TenacityRetryPolicy

    settings = _create_mock_settings(api_key)
    return DefaultAIService(
        api_key=settings.openrouter_api_key,
        api_url=settings.openrouter_api_url,
        text_fast_model=settings.text_fast_model,
        text_reasoning_model=settings.text_reasoning_model,
        ai_timeout=settings.ai_timeout,
        http_client=RequestsHTTPClient(),
        retry_policy=TenacityRetryPolicy(
            ai_retry_attempts=settings.ai_retry_attempts,
            ai_retry_min_wait=settings.ai_retry_min_wait,
            ai_retry_max_wait=settings.ai_retry_max_wait,
        ),
    )


def test_default_ai_service_missing_key_init() -> None:
    from src.domain_models.exceptions import ConfigurationError
    with pytest.raises(ConfigurationError, match="OPENROUTER_API_KEY is required"):
        _create_service(api_key=None)


def test_default_ai_service_invalid_key_length() -> None:
    from src.domain_models.exceptions import ConfigurationError

    with pytest.raises(ConfigurationError, match="API Key must be at least 30 characters long"):
        _create_service(api_key="123")


def test_default_ai_service_invalid_key_format() -> None:
    from src.domain_models.exceptions import ConfigurationError

    with pytest.raises(ConfigurationError, match="API Key format is invalid"):
        _create_service(api_key="invalid_format_key_with_spaces and_tabs")


def test_default_ai_service_calls_generate_summary_valid() -> None:
    ai = _create_service(api_key="sk-or-v1-validkey12345678901234567890")
    with pytest.raises(AIServiceError):
        # Without a mocked network interface, this should raise the AIServiceError (either HTTP/Connection)
        ai.generate_summary("test content")


def test_default_ai_service_calls_generate_question_valid() -> None:
    from src.domain_models.manifest import DocumentMetadataContainer
    ai = _create_service(api_key="sk-or-v1-validkey12345678901234567890")
    node = DocumentNode(
        id="test1",
        parent_id=None,
        title="Test Title",
        content=DocumentContent(summary=None, text=None),
        status=NodeStatus.LOCKED,
        metadata_container=DocumentMetadataContainer(
            metadata=NodeMetadata(source=None, author=None, category=None, time_axis=None),
            ai_metadata=AIProcessingMetadata(
                chunk_id=None, chunk_index=None, entity_metadata={}, hierarchical_tree={}
            ),
        ),
    )
    with pytest.raises(AIServiceError):
        ai.generate_question(node)


def test_default_ai_service_calls_generate_mermaid_valid() -> None:
    ai = _create_service(api_key="sk-or-v1-validkey12345678901234567890")
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
    ai = _create_service(api_key="sk-or-v1-validkey12345678901234567890")
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
