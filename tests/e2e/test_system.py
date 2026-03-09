from src.config import Settings
from src.domain_models.manifest import PipelineContext
from src.domain_models.services import DocumentFactory
from src.infrastructure import InMemoryDocumentRepository
from src.infrastructure.orchestrator import PipelineOrchestrator
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

    settings = Settings(mode="test", default_root_doc_id="root_doc_1")
    orchestrator = PipelineOrchestrator(doc_repo=repo, ai_service=ai, doc_factory=factory)

    # Run the pipeline
    content = "This is a very long business manual about strategy."
    context = PipelineContext(root_doc_id=settings.default_root_doc_id, content=content)
    orchestrator.run_pipeline(context)

    # Verify the results in the repository
    nodes = [
        repo.get_node(settings.default_root_doc_id)
    ]  # Since it's saved as root (parent_id=None)
    assert len(nodes) == 1
    root = nodes[0]

    assert root is not None
    assert root.id == settings.default_root_doc_id
    assert root.content.summary is not None
    assert "System Actor" in root.content.summary
    assert "Action" in root.content.summary
    assert root.metadata.category == "business"
