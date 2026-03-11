import os
from typing import Any
from unittest import mock

import pytest
from cryptography.fernet import Fernet

import main
from src.container import ProductionDIContainer


@pytest.fixture
def mock_env_key() -> Any:
    """Fixture to safely inject a valid encryption key for tests."""
    return mock.patch.dict(
        os.environ, {"MATOME_ENCRYPTION_KEY": Fernet.generate_key().decode("utf-8")}
    )


def test_init_container(mock_env_key: Any) -> None:
    with mock_env_key, mock.patch("src.container.resolve_class") as mock_resolve:
        # To test init_container without implementing services, we mock the resolve_class function
        # to just return our mock interfaces from test_container
        from tests.unit.test_container import (
            MockActiveLearningService,
            MockDocumentProcessingService,
            MockKnowledgeGraphService,
            MockLLMProtocol,
        )

        def llm_factory(*args: Any, **kwargs: Any) -> Any:
            return MockLLMProtocol()

        # Setup the mock to return specific classes based on the string passed
        def side_effect(path: str) -> Any:
            if "LLMProtocol" in path:
                return llm_factory
            if "DocumentProcessingService" in path:
                return MockDocumentProcessingService
            if "KnowledgeGraphService" in path:
                return MockKnowledgeGraphService
            if "ActiveLearningService" in path:
                return MockActiveLearningService
            raise ValueError(path)

        mock_resolve.side_effect = side_effect

        container = main.init_container()
        assert isinstance(container, ProductionDIContainer)
        assert isinstance(container.llm_gateway, MockLLMProtocol)


def test_main_cli_help(capsys: pytest.CaptureFixture[str], mock_env_key: Any) -> None:
    with (
        mock_env_key,
        mock.patch("sys.argv", ["main.py"]),
        mock.patch("main.init_container") as mock_init,
    ):
        # We mock container so we don't try to instantiate abstract protocols
        mock_init.return_value = None
        result = main.main()
        assert result == 0
        captured = capsys.readouterr()
        assert "Hello from matome" in captured.out
