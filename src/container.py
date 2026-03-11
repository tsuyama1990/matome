from collections.abc import Callable

from src.domain_models import PipelineConfig
from src.interfaces import (
    ActiveLearningService,
    DocumentProcessingService,
    KnowledgeGraphService,
    LLMProtocol,
)


class ProductionDIContainer:
    """Dependency Injection container that dynamically initializes components via factories."""

    def __init__(
        self,
        config: PipelineConfig | None,
        llm_gateway_factory: Callable[[], LLMProtocol] | None,
        document_processor_factory: Callable[[], DocumentProcessingService] | None,
        knowledge_graph_factory: Callable[[], KnowledgeGraphService] | None,
        active_learning_factory: Callable[[], ActiveLearningService] | None,
    ) -> None:
        if config is None:
            msg = "PipelineConfig must be provided."
            raise ValueError(msg)
        if llm_gateway_factory is None:
            msg = "LLMProtocol factory must be provided."
            raise ValueError(msg)
        if document_processor_factory is None:
            msg = "DocumentProcessingService factory must be provided."
            raise ValueError(msg)
        if knowledge_graph_factory is None:
            msg = "KnowledgeGraphService factory must be provided."
            raise ValueError(msg)
        if active_learning_factory is None:
            msg = "ActiveLearningService factory must be provided."
            raise ValueError(msg)

        self._config = config

        # Initialize components eagerly from factories
        self._llm_gateway = llm_gateway_factory()
        self._document_processor = document_processor_factory()
        self._knowledge_graph = knowledge_graph_factory()
        self._active_learning = active_learning_factory()

    @property
    def config(self) -> PipelineConfig:
        return self._config

    @property
    def llm_gateway(self) -> LLMProtocol:
        return self._llm_gateway

    @property
    def document_processor(self) -> DocumentProcessingService:
        return self._document_processor

    @property
    def knowledge_graph(self) -> KnowledgeGraphService:
        return self._knowledge_graph

    @property
    def active_learning(self) -> ActiveLearningService:
        return self._active_learning
