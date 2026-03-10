from typing import cast

import pytest

from src.domain_models.interfaces import (
    ClusteringServiceProtocol,
    DocumentRepository,
    EntityExtractorProtocol,
    QuestionServiceProtocol,
    SummaryServiceProtocol,
    TextSplitterProtocol,
    TransactionManager,
)
from src.domain_models.services import DocumentFactory, MetadataService
from src.infrastructure.container import ProductionDIContainer
from src.infrastructure.orchestrator import PipelineConfig, PipelineDependencies


class MockDep:
    pass


def test_production_di_container_success() -> None:
    class DummyDependencies(PipelineDependencies):
        def __init__(self) -> None:
            self.doc_repo = cast(DocumentRepository, MockDep())
            self.transaction_manager = cast(TransactionManager, MockDep())
            self.summary_service = cast(SummaryServiceProtocol, MockDep())
            self.question_service = cast(QuestionServiceProtocol, MockDep())
            self.doc_factory = cast(DocumentFactory, MockDep())
            self.metadata_service = cast(MetadataService, MockDep())
            self.text_splitter = cast(TextSplitterProtocol, MockDep())
            self.entity_extractor = cast(EntityExtractorProtocol, MockDep())
            self.clustering_service = cast(ClusteringServiceProtocol, MockDep())

    deps = DummyDependencies()
    config = PipelineConfig(pipeline_timeout=1.0, raptor_max_clusters=5)
    container = ProductionDIContainer(deps, config)

    ret_deps, ret_config = container.get_dependencies()
    assert ret_deps is deps
    assert ret_config is config


def test_production_di_container_missing_dep() -> None:
    class DummyDependenciesMissing(PipelineDependencies):
        def __init__(self) -> None:
            self.doc_repo = cast(DocumentRepository, MockDep())
            self.transaction_manager = cast(TransactionManager, MockDep())
            self.summary_service = cast(SummaryServiceProtocol, MockDep())
            self.question_service = cast(QuestionServiceProtocol, MockDep())
            self.doc_factory = cast(DocumentFactory, MockDep())
            self.metadata_service = cast(MetadataService, MockDep())
            self.text_splitter = cast(TextSplitterProtocol, MockDep())
            self.entity_extractor = cast(EntityExtractorProtocol, MockDep())
            # missing clustering_service

    deps = DummyDependenciesMissing()
    config = PipelineConfig(pipeline_timeout=1.0, raptor_max_clusters=5)

    with pytest.raises(
        RuntimeError,
        match="DI Container failed to initialize required dependency: clustering_service",
    ):
        ProductionDIContainer(deps, config)
