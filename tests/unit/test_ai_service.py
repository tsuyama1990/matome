import pytest

from src.application.ai import (
    DefaultDiagramService,
    DefaultDocumentGenerationService,
    DefaultEvaluationService,
    DefaultQuestionService,
    DefaultSummaryService,
    DefaultWebGroundingService,
)
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
    monkeypatch: pytest.MonkeyPatch | None = None,
    api_key: str | None = None,
    text_fast_model: str = "google/gemini-2.5-flash",
    text_reasoning_model: str = "deepseek/deepseek-reasoner",
    multimodal_model: str = "openai/gpt-4o",
) -> Settings:

    if monkeypatch:
        if api_key:
            monkeypatch.setenv("OPENROUTER_API_KEY", api_key)
        from pathlib import Path
        dummy_cert = Path(base_dir) / "dummy.pem"
        dummy_cert.write_text("cert")
        monkeypatch.setenv("MATOME_BASE_DATA_DIR", base_dir)
        monkeypatch.setenv("SSL_CERT_PATH", str(dummy_cert))
        monkeypatch.setenv("SPACY_MODEL", "en_core_web_sm")
        monkeypatch.setenv("TRUSTED_SPACY_MODELS", '["en_core_web_sm", "en_core_web_md"]')
        monkeypatch.setenv("CHUNK_SIZE", "1000")
        monkeypatch.setenv("TEXT_FAST_MODEL", text_fast_model)
        monkeypatch.setenv("TEXT_REASONING_MODEL", text_reasoning_model)
        monkeypatch.setenv("MULTIMODAL_MODEL", multimodal_model)
    else:
        import os

        if api_key:
            os.environ["OPENROUTER_API_KEY"] = api_key
        from pathlib import Path
        dummy_cert = Path(base_dir) / "dummy.pem"
        dummy_cert.write_text("cert")
        os.environ["MATOME_BASE_DATA_DIR"] = base_dir
        os.environ["SSL_CERT_PATH"] = str(dummy_cert)
        os.environ["SPACY_MODEL"] = "en_core_web_sm"
        os.environ["TRUSTED_SPACY_MODELS"] = '["en_core_web_sm", "en_core_web_md"]'
        os.environ["CHUNK_SIZE"] = "1000"
        os.environ["TEXT_FAST_MODEL"] = text_fast_model
        os.environ["TEXT_REASONING_MODEL"] = text_reasoning_model
        os.environ["MULTIMODAL_MODEL"] = multimodal_model

    return Settings(
        text_fast_model=text_fast_model,
        text_reasoning_model=text_reasoning_model,
        multimodal_model=multimodal_model,
        allowed_base_dir=base_dir,
        spacy_model="en_core_web_sm",
        trusted_spacy_models=["en_core_web_sm", "en_core_web_md"],
        chunk_size=1000,
    )


def _create_service(
    base_dir: str,
    monkeypatch: pytest.MonkeyPatch | None = None,
    api_key: str | None = None,
    http_client: object = None,
    text_fast_model: str = "google/gemini-2.5-flash",
    text_reasoning_model: str = "deepseek/deepseek-reasoner",
) -> tuple[
    DefaultSummaryService,
    DefaultQuestionService,
    DefaultDiagramService,
    DefaultDocumentGenerationService,
    DefaultWebGroundingService,
    DefaultEvaluationService,
]:
    from unittest.mock import MagicMock

    from src.config import EnvCredentialProvider
    from src.infrastructure.security import PromptInjectionScanner

    settings = _create_mock_settings(
        base_dir=base_dir,
        api_key=api_key,
        text_fast_model=text_fast_model,
        text_reasoning_model=text_reasoning_model,
    )
    provider = EnvCredentialProvider()

    mock_http_client = http_client or MagicMock()

    # We create a dummy retry policy that runs 1 time to bypass Tenacity sleep in tests
    import typing

    class DummyRetry:
        def execute(self, func: typing.Any) -> typing.Any:
            return func()

    # Pass provider directly into http client securely instead of through the communication client
    mock_http_client.credential_provider = provider  # type: ignore[attr-defined]

    from src.infrastructure.ai_client import AIClientFactory

    communication_client = AIClientFactory.create(
        api_url="https://mock.api.url",
        default_model=settings.text_fast_model,
        ai_timeout=settings.ai_timeout,
        http_client=mock_http_client,  # type: ignore
        retry_policy=DummyRetry(),
        security_scanner=PromptInjectionScanner(threshold=0.9),
    )
    security_scanner = PromptInjectionScanner(max_input_length=settings.max_input_length)

    return (
        DefaultSummaryService(
            security_scanner=security_scanner,
            communication_client=communication_client,
            text_fast_model=settings.text_fast_model,
            text_reasoning_model=settings.text_reasoning_model,
        ),
        DefaultQuestionService(
            security_scanner=security_scanner,
            communication_client=communication_client,
            text_fast_model=settings.text_fast_model,
            text_reasoning_model=settings.text_reasoning_model,
        ),
        DefaultDiagramService(
            security_scanner=security_scanner,
            communication_client=communication_client,
            text_fast_model=settings.text_fast_model,
            text_reasoning_model=settings.text_reasoning_model,
        ),
        DefaultDocumentGenerationService(
            security_scanner=security_scanner,
            communication_client=communication_client,
            text_fast_model=settings.text_fast_model,
            text_reasoning_model=settings.text_reasoning_model,
        ),
        DefaultWebGroundingService(
            security_scanner=security_scanner,
            communication_client=communication_client,
            text_fast_model=settings.text_fast_model,
            text_reasoning_model=settings.text_reasoning_model,
        ),
        DefaultEvaluationService(
            security_scanner=security_scanner,
            communication_client=communication_client,
            text_fast_model=settings.text_fast_model,
            text_reasoning_model=settings.text_reasoning_model,
        ),
    )


def test_default_ai_service_missing_key_init(
    tmp_path: pytest.TempPathFactory, monkeypatch: pytest.MonkeyPatch
) -> None:
    from src.config import EnvCredentialProvider
    from src.domain_models.exceptions import ConfigurationError

    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    with pytest.raises(ConfigurationError), EnvCredentialProvider().get_api_key():
        pass


def test_default_ai_service_invalid_key_length(
    tmp_path: pytest.TempPathFactory, monkeypatch: pytest.MonkeyPatch
) -> None:
    from src.config import EnvCredentialProvider
    from src.domain_models.exceptions import ConfigurationError

    monkeypatch.setenv("OPENROUTER_API_KEY", "123")

    with (
        pytest.raises(ConfigurationError, match="API Key validation failed"),
        EnvCredentialProvider().get_api_key(),
    ):
        pass


def test_default_ai_service_invalid_key_format(
    tmp_path: pytest.TempPathFactory, monkeypatch: pytest.MonkeyPatch
) -> None:
    from src.config import EnvCredentialProvider
    from src.domain_models.exceptions import ConfigurationError

    monkeypatch.setenv("OPENROUTER_API_KEY", "invalid_format_key_with_spaces and_tabs")

    with (
        pytest.raises(ConfigurationError, match="API Key validation failed"),
        EnvCredentialProvider().get_api_key(),
    ):
        pass


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

    services = _create_service(
        base_dir=str(tmp_path),
        monkeypatch=monkeypatch,
        api_key="sk-or-v1-validkey12345678901234567890",
        http_client=mock_http,
    )

    summary = services[0].generate_summary("test content")
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

    services = _create_service(
        base_dir=str(tmp_path),
        monkeypatch=monkeypatch,
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

    question = services[1].generate_question(identity, content)
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

    services = _create_service(
        base_dir=str(tmp_path),
        monkeypatch=monkeypatch,
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
    diagram = services[2].generate_mermaid_diagram(board)
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

    services = _create_service(
        base_dir=str(tmp_path),
        monkeypatch=monkeypatch,
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
    diagram = services[3].generate_markdown_requirements(board)
    assert diagram == "# PRD"


def test_default_ai_service_calls_verify_web_grounding_valid(
    tmp_path: pytest.TempPathFactory, monkeypatch: pytest.MonkeyPatch
) -> None:
    from unittest.mock import MagicMock

    mock_http = MagicMock()
    mock_http.post.return_value = {"choices": [{"message": {"content": "No bias found"}}]}

    monkeypatch.setattr(
        "src.infrastructure.security.PromptInjectionScanner.sanitize", lambda self, text: text
    )

    services = _create_service(
        base_dir=str(tmp_path),
        monkeypatch=monkeypatch,
        api_key="sk-or-v1-validkey12345678901234567890",
        http_client=mock_http,
    )
    result = services[4].verify_web_grounding("Some content")
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

    services = _create_service(
        base_dir=str(tmp_path),
        monkeypatch=monkeypatch,
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
    success, response = services[5].evaluate_answer(context)
    assert success is True
    assert "YES" in response
