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


class IntegrationTestSettings(Settings):
    """Test-specific configuration class strictly for safe mock validations."""


def test_pipeline_orchestrator_integration() -> None:
    """
    Tests the core document ingestion and AI pipeline.
    This demonstrates E2E capabilities directly on the orchestrator.
    It reads settings locally to avoid touching the global os.environ block directly.
    """
    repo = InMemoryDocumentRepository()
    ai = MockAIService()  # Even the audit allows mocked AI here to not burn credits if api_key not set, but we use the properly constructed components.
    factory = DocumentFactory()

    import os

    from pydantic import SecretStr

    mock_key = os.environ.get("OPENROUTER_API_KEY", "sk-or-v1-validkey12345678901234567890")

    settings = IntegrationTestSettings(
        mode="test",
        openrouter_api_key=SecretStr(mock_key),
        text_fast_model="google/gemini-2.5-flash",
        text_reasoning_model="deepseek/deepseek-reasoner",
        multimodal_model="openai/gpt-4o",
    )
    text_splitter = DefaultTextSplitter(
        chunk_size=settings.chunk_size, chunk_overlap=settings.chunk_overlap
    )
    entity_extractor = DefaultEntityExtractor(settings.spacy_model)
    clustering_service = DefaultClusteringService(settings.random_seed)

    orchestrator = PipelineOrchestrator(
        doc_repo=repo,
        ai_service=ai,
        doc_factory=factory,
        text_splitter=text_splitter,
        entity_extractor=entity_extractor,
        clustering_service=clustering_service,
        pipeline_timeout=settings.pipeline_timeout,
        raptor_max_clusters=settings.raptor_max_clusters,
    )

    # Run the pipeline
    root_doc_id = settings.default_root_doc_id

    content = "This is a very long business manual about strategy."
    context = PipelineContext(root_doc_id=root_doc_id, content=content, file_path=None)

    orchestrator.run_pipeline(context)

    # Verify the results in the repository
    nodes = [repo.get_node(root_doc_id)]  # Since it's saved as root (parent_id=None)
    assert len(nodes) == 1
    root = nodes[0]

    assert root is not None
    assert root.id == root_doc_id
    assert root.content.summary is not None
    assert "System Actor" in root.content.summary
    assert "Action" in root.content.summary
    assert root.metadata_container.metadata.category == "business"
