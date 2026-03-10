from typing import Protocol

from src.infrastructure.orchestrator import PipelineConfig, PipelineDependencies


class DIContainerProtocol(Protocol):
    def get_dependencies(self) -> tuple[PipelineDependencies, PipelineConfig]: ...


class ProductionDIContainer(DIContainerProtocol):
    """
    Concrete Dependency Injection Container ensuring strict dependency inversion.
    """

    def __init__(
        self,
        dependencies: PipelineDependencies,
        config: PipelineConfig,
    ) -> None:
        self._dependencies = dependencies
        self._config = config

        # Strict DI dependency verification
        for dep_name in [
            "doc_repo",
            "transaction_manager",
            "summary_service",
            "question_service",
            "doc_factory",
            "metadata_service",
            "text_splitter",
            "entity_extractor",
            "clustering_service",
        ]:
            if not getattr(self._dependencies, dep_name, None):
                msg = f"DI Container failed to initialize required dependency: {dep_name}"
                raise RuntimeError(msg)

    def get_dependencies(self) -> tuple[PipelineDependencies, PipelineConfig]:
        return self._dependencies, self._config
