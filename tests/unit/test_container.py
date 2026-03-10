import pytest

from src.infrastructure.container import ProductionDIContainer
from src.infrastructure.orchestrator import PipelineConfig, PipelineDependencies


class MockDep:
    pass


def test_production_di_container_success():
    class DummyDependencies(PipelineDependencies):
        def __init__(self) -> None:
            self.doc_repo = MockDep()
            self.transaction_manager = MockDep()
            self.summary_service = MockDep()
            self.question_service = MockDep()
            self.doc_factory = MockDep()
            self.metadata_service = MockDep()
            self.text_splitter = MockDep()
            self.entity_extractor = MockDep()
            self.clustering_service = MockDep()

    deps = DummyDependencies()
    config = PipelineConfig(pipeline_timeout=1.0, raptor_max_clusters=5)
    container = ProductionDIContainer(deps, config)

    ret_deps, ret_config = container.get_dependencies()
    assert ret_deps is deps
    assert ret_config is config


def test_production_di_container_missing_dep():
    class DummyDependenciesMissing(PipelineDependencies):
        def __init__(self) -> None:
            self.doc_repo = MockDep()
            self.transaction_manager = MockDep()
            self.summary_service = MockDep()
            self.question_service = MockDep()
            self.doc_factory = MockDep()
            self.metadata_service = MockDep()
            self.text_splitter = MockDep()
            self.entity_extractor = MockDep()
            # missing clustering_service

    deps = DummyDependenciesMissing()
    config = PipelineConfig(pipeline_timeout=1.0, raptor_max_clusters=5)

    with pytest.raises(
        RuntimeError,
        match="DI Container failed to initialize required dependency: clustering_service",
    ):
        ProductionDIContainer(deps, config)
