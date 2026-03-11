from src.container import ProductionDIContainer
from src.domain_models.config import PipelineConfig
from src.services.document import DefaultDocumentProcessingService
from src.services.graph import DefaultKnowledgeGraphService
from src.services.learning import DefaultActiveLearningService
from src.services.llm import DefaultLLMProtocol


def init_container() -> ProductionDIContainer:
    """Initialize the configuration and DI container for the application."""
    config = PipelineConfig()

    # Define factories for production services
    def llm_factory() -> DefaultLLMProtocol:
        return DefaultLLMProtocol()

    def doc_factory() -> DefaultDocumentProcessingService:
        return DefaultDocumentProcessingService()

    def kg_factory() -> DefaultKnowledgeGraphService:
        return DefaultKnowledgeGraphService()

    def al_factory() -> DefaultActiveLearningService:
        return DefaultActiveLearningService()

    return ProductionDIContainer(
        config=config,
        llm_gateway_factory=llm_factory,
        document_processor_factory=doc_factory,
        knowledge_graph_factory=kg_factory,
        active_learning_factory=al_factory,
    )
