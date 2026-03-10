import pytest

from src.config import Settings
from src.domain_models.manifest import PipelineContext
from src.domain_models.services import DocumentFactory, MetadataService
from src.infrastructure import InMemoryDocumentRepository
from src.infrastructure.orchestrator import (
    PipelineConfig,
    PipelineDependencies,
    PipelineOrchestrator,
)
from tests.helpers.mocks import MockAIService


class IntegrationTestSettings(Settings):
    """Test-specific configuration class strictly for safe mock validations."""


def test_pipeline_orchestrator_integration(tmp_path: pytest.TempPathFactory) -> None:
    """
    Tests the core document ingestion and AI pipeline.
    This demonstrates E2E capabilities directly on the orchestrator.
    It reads settings locally to avoid touching the global os.environ block directly.
    """
    repo = InMemoryDocumentRepository()
    ai = MockAIService()  # Even the audit allows mocked AI here to not burn credits if api_key not set, but we use the properly constructed components.
    factory = DocumentFactory()
    metadata_service = MetadataService()

    from pydantic import SecretStr
    settings = IntegrationTestSettings(
        openrouter_api_url=SecretStr("https://mock.api.url"),
        text_fast_model="google/gemini-2.5-flash",
        text_reasoning_model="deepseek/deepseek-reasoner",
        multimodal_model="openai/gpt-4o",
        allowed_base_dir=str(tmp_path),
    )

    from src.infrastructure.services import (
        DefaultClusteringService,
        DefaultTextSplitter,
        LangChainSplitterStrategy,
    )

    text_splitter = DefaultTextSplitter(
        chunk_size=settings.chunk_size,
        chunk_overlap=settings.chunk_overlap,
        max_file_size=settings.max_file_size,
        strategy=LangChainSplitterStrategy(),
    )
    from src.infrastructure.services import EntityExtractorBuilder
    entity_extractor = EntityExtractorBuilder.build(
        settings.spacy_model, settings.trusted_spacy_models, settings.trusted_model_hashes
    )
    clustering_service = DefaultClusteringService(settings.random_seed)

    deps = PipelineDependencies(
        doc_repo=repo,
        transaction_manager=repo,
        summary_service=ai,
        question_service=ai,
        doc_factory=factory,
        metadata_service=metadata_service,
        text_splitter=text_splitter,
        entity_extractor=entity_extractor,
        clustering_service=clustering_service,
    )
    config = PipelineConfig(
        pipeline_timeout=settings.pipeline_timeout,
        raptor_max_clusters=settings.raptor_max_clusters,
    )
    orchestrator = PipelineOrchestrator(dependencies=deps, config=config)

    # Run the pipeline
    root_doc_id = settings.default_root_doc_id

    content_text = "This is a very long business manual about strategy."
    context = PipelineContext(root_doc_id=root_doc_id, content=content_text, file_path=None)

    orchestrator.run_pipeline(context)

    # Verify the results in the repository
    identity = repo.get_identity(root_doc_id)
    content_node = repo.get_content(root_doc_id)

    assert identity is not None
    assert content_node is not None
    assert identity.id == root_doc_id
    assert content_node.summary is not None
    assert "System Actor" in content_node.summary
    assert "Action" in content_node.summary

    metadata = metadata_service.get_metadata(identity.id)
    assert metadata is not None
    assert metadata.metadata.category == "business"
