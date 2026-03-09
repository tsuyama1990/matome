from src.config import Settings
from src.domain_models.services import DocumentFactory
from src.infrastructure import InMemoryDocumentRepository
from src.infrastructure.orchestrator import PipelineOrchestrator
from tests.helpers.mocks import MockAIService


def test_pipeline_orchestrator_integration() -> None:
    """
    Tests the core document ingestion and AI pipeline.
    This demonstrates E2E capabilities directly on the orchestrator, mocking dependencies appropriately.
    """
    repo = InMemoryDocumentRepository()
    ai = MockAIService()
    factory = DocumentFactory(ai_service=ai)
    settings = Settings(mode="test")
    orchestrator = PipelineOrchestrator(
        doc_repo=repo, ai_service=ai, settings=settings, doc_factory=factory
    )

    # Run the pipeline
    content = "This is a very long business manual about strategy."
    orchestrator.run_pipeline(content)

    # Verify the results in the repository
    nodes = [
        repo.get_node(settings.default_root_doc_id)
    ]  # Since it's saved as root (parent_id=None)
    assert len(nodes) == 1
    root = nodes[0]

    assert root is not None
    assert root.id == settings.default_root_doc_id
    assert root.content.summary is not None
    assert "CoD Summary of: " in root.content.summary
    assert root.metadata.category == "business"
