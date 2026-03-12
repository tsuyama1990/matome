import os
from typing import Any
from unittest import mock

import pytest
from cryptography.fernet import Fernet

from src.container import ProductionDIContainer, resolve_class
from src.document import DocumentProcessor
from src.domain_models import PipelineConfig
from src.infrastructure.openrouter import OpenRouterGateway
from src.interfaces import BaseTestActiveLearningService, BaseTestKnowledgeGraphService


@pytest.fixture
def mock_env_key() -> Any:
    return mock.patch.dict(
        os.environ, {"MATOME_ENCRYPTION_KEY": Fernet.generate_key().decode("utf-8")}
    )


def test_resolve_class() -> None:
    # Test valid resolution
    cls = resolve_class("src.container.ProductionDIContainer")
    assert cls is ProductionDIContainer

    # Test not a callable
    with pytest.raises(TypeError, match="Resolved object __name__ is not callable."):
        resolve_class("src.container.__name__")

    # Test invalid module
    with pytest.raises(ImportError):
        resolve_class("invalid.module.Class")


def test_container_initialization_success(mock_env_key: Any) -> None:
    with mock_env_key, mock.patch("socket.gethostbyname", return_value="8.8.8.8"):
        config = PipelineConfig(
            llm_service_path="src.infrastructure.openrouter.OpenRouterGateway",
            document_service_path="src.document.DocumentProcessor",
        )

        container = ProductionDIContainer(
            llm_gateway_factory=ProductionDIContainer._build_llm_factory(config),
            document_processor_factory=ProductionDIContainer._build_document_factory(config),
            knowledge_graph_factory=ProductionDIContainer._build_knowledge_graph_factory(config),
            active_learning_factory=ProductionDIContainer._build_active_learning_factory(config),
            config=config,
        )

        assert container.config is config
        assert isinstance(container.llm_gateway, OpenRouterGateway)
        assert isinstance(container.document_processor, DocumentProcessor)
        assert isinstance(container.knowledge_graph, BaseTestKnowledgeGraphService)
        assert isinstance(container.active_learning, BaseTestActiveLearningService)

def test_container_initialization_failures(mock_env_key: Any) -> None:
    with mock_env_key:
        config = PipelineConfig()

        # Type errors for non-callables
        with pytest.raises(
            TypeError, match="llm_gateway_factory must be a callable factory function."
        ):
            ProductionDIContainer(
                "Not a callable factory",  # type: ignore[arg-type]
                ProductionDIContainer._build_document_factory(config),
                ProductionDIContainer._build_knowledge_graph_factory(config),
                ProductionDIContainer._build_active_learning_factory(config),
                config,
            )
