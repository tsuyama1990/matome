import pytest

from src.application.ai import DefaultAIService
from src.config import Settings
from src.domain_models import (
    ContentNode,
    IdentityNode,
    NodeStatus,
    PivotAxis,
    PivotBoard,
    PivotBoardViewNode,
    UserInteractionContext,
)


def _create_mock_settings(
    base_dir: str,
    api_key: str | None = None,
    text_fast_model: str = "google/gemini-2.5-flash",
    text_reasoning_model: str = "deepseek/deepseek-reasoner",
    multimodal_model: str = "openai/gpt-4o",
) -> Settings:

    # Completely isolate tests from os.environ side-effects and avoid hardcoded secrets where unnecessary
    # Pass dynamically resolved secret or mock parameter directly to Settings constructor
    # Since pydantic validator catches invalid secrets, we can test validation behaviors here.
    import os

    if api_key:
        os.environ["OPENROUTER_API_KEY"] = api_key
    from src.config import CredentialConfig

    return Settings(
        credentials=CredentialConfig(),
        openrouter_api_url="https://mock.api.url",
        text_fast_model=text_fast_model,
        text_reasoning_model=text_reasoning_model,
        multimodal_model=multimodal_model,
        allowed_base_dir=base_dir,
    )


def _create_service(
    base_dir: str,
    api_key: str | None = None,
    http_client: object = None,
    text_fast_model: str = "google/gemini-2.5-flash",
    text_reasoning_model: str = "deepseek/deepseek-reasoner",
) -> DefaultAIService:
    from unittest.mock import MagicMock

    from src.config import EnvCredentialProvider
    from src.infrastructure.ai_client import DefaultAICommunicationClient
    from src.infrastructure.security import PromptInjectionScanner

    settings = _create_mock_settings(
        base_dir=base_dir,
        api_key=api_key,
        text_fast_model=text_fast_model,
        text_reasoning_model=text_reasoning_model,
    )
    provider = EnvCredentialProvider(settings.credentials)

    mock_http_client = http_client or MagicMock()

    # We create a dummy retry policy that runs 1 time to bypass Tenacity sleep in tests
    import typing

    class DummyRetry:
        def execute(self, func: typing.Any) -> typing.Any:
            return func()

    # Pass provider directly into http client securely instead of through the communication client
    mock_http_client.credential_provider = provider  # type: ignore[attr-defined]

    communication_client = DefaultAICommunicationClient(
        credential_provider=provider,
        api_url=settings.openrouter_api_url,
        default_model=settings.text_fast_model,
        ai_timeout=settings.ai_timeout,
        http_client=mock_http_client,  # type: ignore
        retry_policy=DummyRetry(),
    )
    security_scanner = PromptInjectionScanner()

    return DefaultAIService(
        security_scanner=security_scanner,
        communication_client=communication_client,
        text_fast_model=settings.text_fast_model,
        text_reasoning_model=settings.text_reasoning_model,
    )


def test_default_ai_service_missing_key_init(
    tmp_path: pytest.TempPathFactory, monkeypatch: pytest.MonkeyPatch
) -> None:
    from src.config import EnvCredentialProvider
    from src.domain_models.exceptions import ConfigurationError

    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    with pytest.raises(ConfigurationError):
        EnvCredentialProvider().get_api_key()


def test_default_ai_service_invalid_key_length(
    tmp_path: pytest.TempPathFactory, monkeypatch: pytest.MonkeyPatch
) -> None:
    from src.config import EnvCredentialProvider
    from src.domain_models.exceptions import ConfigurationError

    monkeypatch.setenv("OPENROUTER_API_KEY", "123")
    with pytest.raises(ConfigurationError, match="API Key must be at least 30 characters long"):
        EnvCredentialProvider().get_api_key()


def test_default_ai_service_invalid_key_format(
    tmp_path: pytest.TempPathFactory, monkeypatch: pytest.MonkeyPatch
) -> None:
    from src.config import EnvCredentialProvider
    from src.domain_models.exceptions import ConfigurationError

    monkeypatch.setenv("OPENROUTER_API_KEY", "invalid_format_key_with_spaces and_tabs")
    with pytest.raises(ConfigurationError, match="API Key format is invalid"):
        EnvCredentialProvider().get_api_key()


def test_default_ai_service_calls_generate_summary_valid(
    tmp_path: pytest.TempPathFactory, monkeypatch: pytest.MonkeyPatch
) -> None:
    from unittest.mock import MagicMock

    mock_http = MagicMock()
    mock_http.post.return_value = {"choices": [{"message": {"content": "mock summary"}}]}

    # Mock the scanner so it doesn't try to load HF models in pure unit tests
    monkeypatch.setattr(
        "src.infrastructure.security.PromptInjectionScanner.sanitize", lambda self, text: text
    )

    ai = _create_service(
        base_dir=str(tmp_path),
        api_key="sk-or-v1-validkey12345678901234567890",
        http_client=mock_http,
    )

    summary = ai.generate_summary("test content")
    assert summary == "mock summary"


def test_default_ai_service_calls_generate_question_valid(
    tmp_path: pytest.TempPathFactory, monkeypatch: pytest.MonkeyPatch
) -> None:
    from unittest.mock import MagicMock

    mock_http = MagicMock()
    mock_http.post.return_value = {"choices": [{"message": {"content": "mock question"}}]}

    monkeypatch.setattr(
        "src.infrastructure.security.PromptInjectionScanner.sanitize", lambda self, text: text
    )

    ai = _create_service(
        base_dir=str(tmp_path),
        api_key="sk-or-v1-validkey12345678901234567890",
        http_client=mock_http,
    )
    identity = IdentityNode(
        id="test1",
        parent_id=None,
        title="Test Title",
        status=NodeStatus.LOCKED,
    )
    content = ContentNode(node_id="test1", summary=None, text=None)

    question = ai.generate_question(identity, content)
    assert question == "mock question"


def test_default_ai_service_calls_generate_mermaid_valid(
    tmp_path: pytest.TempPathFactory, monkeypatch: pytest.MonkeyPatch
) -> None:
    from unittest.mock import MagicMock

    mock_http = MagicMock()
    mock_http.post.return_value = {"choices": [{"message": {"content": "graph TD"}}]}

    monkeypatch.setattr(
        "src.infrastructure.security.PromptInjectionScanner.sanitize", lambda self, text: text
    )

    ai = _create_service(
        base_dir=str(tmp_path),
        api_key="sk-or-v1-validkey12345678901234567890",
        http_client=mock_http,
    )
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
    assert diagram == "graph TD"


def test_default_ai_service_calls_generate_markdown_valid(
    tmp_path: pytest.TempPathFactory, monkeypatch: pytest.MonkeyPatch
) -> None:
    from unittest.mock import MagicMock

    mock_http = MagicMock()
    mock_http.post.return_value = {"choices": [{"message": {"content": "# PRD"}}]}

    monkeypatch.setattr(
        "src.infrastructure.security.PromptInjectionScanner.sanitize", lambda self, text: text
    )

    ai = _create_service(
        base_dir=str(tmp_path),
        api_key="sk-or-v1-validkey12345678901234567890",
        http_client=mock_http,
    )
    board = PivotBoard(
        id="board_1",
        original_root_id="root_1",
        axis=PivotAxis.ACTOR_STATE,
        custom_axis_description=None,
        nodes=[
            PivotBoardViewNode(node_id="test1", x_position=0.1, y_position=0.2, cluster_id=None)
        ],
    )
    diagram = ai.generate_markdown_requirements(board)
    assert diagram == "# PRD"


def test_default_ai_service_calls_verify_web_grounding_valid(
    tmp_path: pytest.TempPathFactory,
) -> None:
    from unittest.mock import MagicMock

    mock_http = MagicMock()
    mock_http.post.return_value = {"choices": [{"message": {"content": "No bias found"}}]}

    ai = _create_service(
        base_dir=str(tmp_path),
        api_key="sk-or-v1-validkey12345678901234567890",
        http_client=mock_http,
    )
    result = ai.verify_web_grounding("Some content")
    assert result == "No bias found"


def test_default_ai_service_calls_evaluate_answer_valid(
    tmp_path: pytest.TempPathFactory, monkeypatch: pytest.MonkeyPatch
) -> None:
    from unittest.mock import MagicMock

    mock_http = MagicMock()
    mock_http.post.return_value = {"choices": [{"message": {"content": "YES it is correct"}}]}

    monkeypatch.setattr(
        "src.infrastructure.security.PromptInjectionScanner.sanitize", lambda self, text: text
    )

    ai = _create_service(
        base_dir=str(tmp_path),
        api_key="sk-or-v1-validkey12345678901234567890",
        http_client=mock_http,
    )
    context = UserInteractionContext(
        node_id="test1",
        status=NodeStatus.LOCKED,
        question_asked="What?",
        user_answer="budget > 5000",
        feedback=None,
        hints_used=0,
    )
    success, response = ai.evaluate_answer(context)
    assert success is True
    assert "YES" in response
