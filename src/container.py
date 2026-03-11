from collections.abc import Callable

from src.domain_models import PipelineConfig
from src.interfaces import (
    ActiveLearningService,
    DocumentProcessingService,
    KnowledgeGraphService,
    LLMProtocol,
)


class ProductionDIContainer:
    """Dependency Injection container that dynamically initializes components via factory functions."""

    def __init__(
        self,
        config: PipelineConfig,
        llm_gateway_factory: Callable[[], LLMProtocol],
        document_processor_factory: Callable[[], DocumentProcessingService],
        knowledge_graph_factory: Callable[[], KnowledgeGraphService],
        active_learning_factory: Callable[[], ActiveLearningService],
    ) -> None:
        # Strict DI instantiation requires all parameters explicitly provided as factory callbacks.
        if config is None:
            msg = "PipelineConfig must be explicitly provided."
            raise ValueError(msg)
        if llm_gateway_factory is None:
            msg = "LLMProtocol factory function must be explicitly provided."
            raise ValueError(msg)
        if document_processor_factory is None:
            msg = "DocumentProcessingService factory function must be explicitly provided."
            raise ValueError(msg)
        if knowledge_graph_factory is None:
            msg = "KnowledgeGraphService factory function must be explicitly provided."
            raise ValueError(msg)
        if active_learning_factory is None:
            msg = "ActiveLearningService factory function must be explicitly provided."
            raise ValueError(msg)

        if not callable(llm_gateway_factory):
            msg = "llm_gateway_factory must be a callable factory function."
            raise TypeError(msg)
        if not callable(document_processor_factory):
            msg = "document_processor_factory must be a callable factory function."
            raise TypeError(msg)
        if not callable(knowledge_graph_factory):
            msg = "knowledge_graph_factory must be a callable factory function."
            raise TypeError(msg)
        if not callable(active_learning_factory):
            msg = "active_learning_factory must be a callable factory function."
            raise TypeError(msg)

        self._config = config

        # Initialize components dynamically strictly from factories
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
