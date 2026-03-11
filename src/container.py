from collections.abc import Callable

from src.domain_models import PipelineConfig
from src.interfaces import (
    ActiveLearningService,
    DocumentProcessingService,
    KnowledgeGraphService,
    LLMProtocol,
)


class ProductionDIContainer:
    """Dependency Injection container that dynamically initializes components via factories or direct instances."""

    def __init__(
        self,
        config: PipelineConfig,
        llm_gateway_factory: LLMProtocol | Callable[[], LLMProtocol],
        document_processor_factory: DocumentProcessingService | Callable[[], DocumentProcessingService],
        knowledge_graph_factory: KnowledgeGraphService | Callable[[], KnowledgeGraphService],
        active_learning_factory: ActiveLearningService | Callable[[], ActiveLearningService]
    ) -> None:
        # Pydantic handles null-safety for config if typing is strict, but we can double check defensively.
        if config is None:
            msg = "PipelineConfig must be explicitly provided."
            raise ValueError(msg)
        if llm_gateway_factory is None:
            msg = "LLMProtocol factory or instance must be explicitly provided."
            raise ValueError(msg)
        if document_processor_factory is None:
            msg = "DocumentProcessingService factory or instance must be explicitly provided."
            raise ValueError(msg)
        if knowledge_graph_factory is None:
            msg = "KnowledgeGraphService factory or instance must be explicitly provided."
            raise ValueError(msg)
        if active_learning_factory is None:
            msg = "ActiveLearningService factory or instance must be explicitly provided."
            raise ValueError(msg)

        self._config = config

        # Initialize components eagerly from factories, or use direct instances if passed
        self._llm_gateway = llm_gateway_factory() if callable(llm_gateway_factory) else llm_gateway_factory
        self._document_processor = document_processor_factory() if callable(document_processor_factory) else document_processor_factory
        self._knowledge_graph = knowledge_graph_factory() if callable(knowledge_graph_factory) else knowledge_graph_factory
        self._active_learning = active_learning_factory() if callable(active_learning_factory) else active_learning_factory

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
