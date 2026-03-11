from src.domain_models import PipelineConfig
from src.interfaces import (
    ActiveLearningService,
    DocumentProcessingService,
    KnowledgeGraphService,
    LLMProtocol,
)


class ProductionDIContainer:
    """Dependency Injection container that rigorously validates component initialization."""

    def __init__(
        self,
        config: PipelineConfig,
        llm_gateway: LLMProtocol,
        document_processor: DocumentProcessingService,
        knowledge_graph: KnowledgeGraphService,
        active_learning: ActiveLearningService,
    ) -> None:
        if not config:
            msg = "PipelineConfig must be provided."
            raise ValueError(msg)
        if not llm_gateway:
            msg = "LLMProtocol implementation must be provided."
            raise ValueError(msg)
        if not document_processor:
            msg = "DocumentProcessingService implementation must be provided."
            raise ValueError(msg)
        if not knowledge_graph:
            msg = "KnowledgeGraphService implementation must be provided."
            raise ValueError(msg)
        if not active_learning:
            msg = "ActiveLearningService implementation must be provided."
            raise ValueError(msg)

        self._config = config
        self._llm_gateway = llm_gateway
        self._document_processor = document_processor
        self._knowledge_graph = knowledge_graph
        self._active_learning = active_learning

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
