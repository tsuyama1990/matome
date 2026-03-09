from src.config import Settings
from src.domain_models.manifest import PipelineContext
from src.domain_models.services import DocumentFactory
from src.infrastructure import InMemoryDocumentRepository
from src.infrastructure.orchestrator import PipelineOrchestrator
from tests.helpers.mocks import MockAIService


def test_pipeline_orchestrator_integration() -> None:
    """
    Tests the core document ingestion and AI pipeline.
    This demonstrates E2E capabilities directly on the orchestrator, mocking dependencies appropriately.
    """
    import os

    os.environ["MODE"] = "test"
    os.environ["DEFAULT_AI_MODEL"] = "google/gemini-2.5-flash"
    os.environ["DEFAULT_ROOT_DOC_ID"] = "root_doc_1"

    repo = InMemoryDocumentRepository()
    ai = MockAIService()
    factory = DocumentFactory()
    settings = Settings()
    orchestrator = PipelineOrchestrator(doc_repo=repo, ai_service=ai, doc_factory=factory)

    # Run the pipeline
    content = "This is a very long business manual about strategy."
    context = PipelineContext(
        root_doc_id=settings.default_root_doc_id,
        content=content
    )
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
    assert "CoD Summary of: " in root.content.summary
    assert root.metadata.category == "business"
