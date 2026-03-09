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

    from pydantic import SecretStr
    settings = IntegrationTestSettings(
        mode="test",
        openrouter_api_key=SecretStr("sk-or-v1-validkey12345678901234567890"),
        text_fast_model="google/gemini-2.5-flash",
        text_reasoning_model="deepseek/deepseek-reasoner",
        multimodal_model="openai/gpt-4o",
    )
    text_splitter = DefaultTextSplitter(
        chunk_size=settings.chunk_size, chunk_overlap=settings.chunk_overlap
    )
    entity_extractor = DefaultEntityExtractor()
    clustering_service = DefaultClusteringService()

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
    from src.domain_models.constants import ROOT_DOC_ID

    content = "This is a very long business manual about strategy."
    context = PipelineContext(root_doc_id=ROOT_DOC_ID, content=content, file_path=None)

    orchestrator.run_pipeline(context)

    # Verify the results in the repository
    nodes = [repo.get_node(ROOT_DOC_ID)]  # Since it's saved as root (parent_id=None)
    assert len(nodes) == 1
    root = nodes[0]

    assert root is not None
    assert root.id == ROOT_DOC_ID
    assert root.content.summary is not None
    assert "System Actor" in root.content.summary
    assert "Action" in root.content.summary
    assert root.metadata_container.metadata.category == "business"
