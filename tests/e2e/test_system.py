from src.config import Settings
from src.infrastructure import InMemoryDocumentRepository, MockAIService
from src.infrastructure.orchestrator import PipelineOrchestrator


def test_pipeline_orchestrator_integration() -> None:
    """
    Tests the core document ingestion and AI pipeline.
    This demonstrates E2E capabilities directly on the orchestrator, mocking dependencies appropriately.
    """
    repo = InMemoryDocumentRepository()
    ai = MockAIService()
    settings = Settings(mode="test")
    orchestrator = PipelineOrchestrator(doc_repo=repo, ai_service=ai, settings=settings)

    # Run the pipeline
    orchestrator.run_pipeline()

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
