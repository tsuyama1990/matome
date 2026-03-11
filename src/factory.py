import os

from src.container import ProductionDIContainer
from src.domain_models.config import PipelineConfig


def init_container() -> ProductionDIContainer:
    """Initialize the configuration and DI container for the application."""
    config = PipelineConfig()

    # Since production services aren't built in Cycle 1, we use a placeholder factory.
    # We will raise NotImplementedError unless MOCKS are explicitly enabled in environment
    # for testing purposes only. No test imports are present in the global scope.

    use_mocks = os.environ.get("USE_MOCKS") == "1"

    if use_mocks:
        # We only import mocks if explicitly running in mock mode to prevent
        # production dependency on test code.
        from tests.unit.test_container import (
            MockActiveLearningService,
            MockDocumentProcessingService,
            MockKnowledgeGraphService,
            MockLLMProtocol,
        )

        def llm_factory() -> MockLLMProtocol:
            return MockLLMProtocol()

        def doc_factory() -> MockDocumentProcessingService:
            return MockDocumentProcessingService()

        def kg_factory() -> MockKnowledgeGraphService:
            return MockKnowledgeGraphService()

        def al_factory() -> MockActiveLearningService:
            return MockActiveLearningService()
    else:
        # In a real environment, we'd inject concrete classes here.
        # Since this is Cycle 01, we cannot load what doesn't exist yet.
        msg = "Production implementations for services are not yet built. Set USE_MOCKS=1 to run dummy implementations."
        raise NotImplementedError(msg)

    return ProductionDIContainer(
        config=config,
        llm_gateway_factory=llm_factory,
        document_processor_factory=doc_factory,
        knowledge_graph_factory=kg_factory,
        active_learning_factory=al_factory,
    )
