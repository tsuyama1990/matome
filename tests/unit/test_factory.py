import os
import pytest
from unittest import mock

from src.factory import init_container
from src.container import ProductionDIContainer

def test_init_container_with_mocks() -> None:
    with mock.patch.dict(os.environ, {"USE_MOCKS": "1"}):
        container = init_container()
        assert isinstance(container, ProductionDIContainer)
        assert container.llm_gateway is not None
        assert container.document_processor is not None
        assert container.knowledge_graph is not None
        assert container.active_learning is not None

def test_init_container_without_mocks() -> None:
    with mock.patch.dict(os.environ, {}, clear=True):
        container = init_container()
        assert isinstance(container, ProductionDIContainer)
        assert container.llm_gateway is not None
        assert container.document_processor is not None
        assert container.knowledge_graph is not None
        assert container.active_learning is not None
