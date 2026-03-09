from src.config import Settings
from src.domain_models.manifest import PipelineContext
from src.domain_models.services import DocumentFactory
from src.infrastructure import InMemoryDocumentRepository
from src.infrastructure.orchestrator import PipelineOrchestrator
from src.infrastructure.services import (
    DefaultClusteringService,
    DefaultEntityExtractor,
    DefaultTextSplitter,
)
from tests.helpers.mocks import MockAIService


def test_pipeline_orchestrator_integration() -> None:
    """
    Tests the core document ingestion and AI pipeline.
    This demonstrates E2E capabilities directly on the orchestrator.
    It reads settings locally to avoid touching the global os.environ block directly.
    """
    repo = InMemoryDocumentRepository()
    ai = MockAIService()  # Even the audit allows mocked AI here to not burn credits if api_key not set, but we use the properly constructed components.
    factory = DocumentFactory()

    settings = Settings(mode="test")
    text_splitter = DefaultTextSplitter(chunk_size=1000, chunk_overlap=100)
    entity_extractor = DefaultEntityExtractor()
    clustering_service = DefaultClusteringService()

    orchestrator = PipelineOrchestrator(
        doc_repo=repo,
        ai_service=ai,
        doc_factory=factory,
        text_splitter=text_splitter,
        entity_extractor=entity_extractor,
        clustering_service=clustering_service,
        settings=settings,
    )

    # Run the pipeline
    from src.domain_models.constants import ROOT_DOC_ID
    content = "This is a very long business manual about strategy."
    context = PipelineContext(root_doc_id=ROOT_DOC_ID, content=content)
    orchestrator.run_pipeline(context)

    # Verify the results in the repository
    nodes = [
        repo.get_node(ROOT_DOC_ID)
    ]  # Since it's saved as root (parent_id=None)
    assert len(nodes) == 1
    root = nodes[0]

    assert root is not None
    assert root.id == ROOT_DOC_ID
    assert root.content.summary is not None
    assert "System Actor" in root.content.summary
    assert "Action" in root.content.summary
    assert root.metadata.category == "business"
