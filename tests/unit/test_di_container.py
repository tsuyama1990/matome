import pytest

from src.di_container import ProductionDIContainer
from src.domain_models.config import PipelineConfig


def test_di_container_init() -> None:
    config = PipelineConfig()
    container = ProductionDIContainer(config=config)
    assert container.config == config
    assert container.llm_gateway_factory is None
    assert container.vector_repo_factory is None

def test_resolve_service_import_error() -> None:
    config = PipelineConfig()
    container = ProductionDIContainer(config=config)

    with pytest.raises(ImportError, match="Failed to resolve service"):
        container._resolve_service("non.existent.Module", object)


class MockService:
    pass

def test_resolve_service_success() -> None:
    import tests.unit.test_di_container
    config = PipelineConfig()
    container = ProductionDIContainer(config=config)

    # Path inside this very module
    service = container._resolve_service("tests.unit.test_di_container.MockService", tests.unit.test_di_container.MockService)
    assert isinstance(service, tests.unit.test_di_container.MockService)

def test_resolve_service_type_mismatch() -> None:
    config = PipelineConfig()
    container = ProductionDIContainer(config=config)

    with pytest.raises(ImportError, match="Failed to resolve service"):
        container._resolve_service("tests.unit.test_di_container.MockService", int)
