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
        os.environ,
        {
            "MATOME_ENCRYPTION_KEY": Fernet.generate_key().decode("utf-8"),
            "MATOME_SALT": "secure_random_salt_for_testing_12345",
        },
    )


def test_init_container(mock_env_key: Any) -> None:
    with (
        mock_env_key,
        mock.patch("socket.gethostbyname", return_value="8.8.8.8"),
        mock.patch("main.PipelineConfig") as mock_config_class,
    ):
        from src.domain_models.config import PipelineConfig

        # Use the actual real service paths so the test uses genuine DI without mock protocols
        mock_config = PipelineConfig(
            llm_service_path="src.infrastructure.openrouter.GenericLLMGateway",
            document_service_path="src.document.DocumentProcessor",
            graph_service_path="tests.mocks.services.BaseTestKnowledgeGraphService",
            active_learning_service_path="tests.mocks.services.BaseTestActiveLearningService",
        )
        mock_config_class.return_value = mock_config

        container = main.init_container()
        assert isinstance(container, ProductionDIContainer)

        from src.infrastructure.openrouter import GenericLLMGateway

        assert isinstance(container.llm_gateway, GenericLLMGateway)


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
