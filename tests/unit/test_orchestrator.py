from pydantic import SecretStr

from src.config import Settings
from src.domain_models import DocumentFactory, MetadataService
from src.infrastructure import InMemoryDocumentRepository
from src.infrastructure.orchestrator import (
    PipelineConfig,
    PipelineDependencies,
    PipelineOrchestrator,
)
from src.infrastructure.services import (
    ServiceFactory,
)
from tests.helpers.mocks import MockAIService


def _create_orchestrator() -> PipelineOrchestrator:
    settings = Settings(
        openrouter_api_key=SecretStr("sk-or-v1-validkey12345678901234567890"),
        text_fast_model="google/gemini-2.5-flash",
        text_reasoning_model="deepseek/deepseek-reasoner",
        multimodal_model="openai/gpt-4o",
    )
    repo = InMemoryDocumentRepository()
    ai = MockAIService()
    factory = DocumentFactory()
    metadata_service = MetadataService()
    text_splitter = ServiceFactory.create_text_splitter(
        chunk_size=settings.chunk_size, chunk_overlap=settings.chunk_overlap
    )
    entity_extractor = ServiceFactory.create_entity_extractor(settings.spacy_model)
    clustering_service = ServiceFactory.create_clustering_service(settings.random_seed)

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
    return PipelineOrchestrator(dependencies=deps, config=config)


def test_orchestrator_chunking_fallback() -> None:
    orchestrator = _create_orchestrator()
    chunks = orchestrator.deps.text_splitter.split_text("test " * 1000)
    assert len(chunks) > 0
    assert "test" in chunks[0]


def test_orchestrator_ner_fallback() -> None:
    orchestrator = _create_orchestrator()
    entities = orchestrator.deps.entity_extractor.extract_entities(["test chunk 1", "test chunk 2"])
    # May use Spacy if present, or fallback. Ensure it returns a dictionary.
    assert isinstance(entities, dict)


def test_orchestrator_raptor_fallback() -> None:
    orchestrator = _create_orchestrator()
    # Pass more than 15 chunks to avoid the UMAP dimensionality error for N <= 15 when using defaults
    chunks = [f"test document chunk number {i}" for i in range(20)]
    tree = orchestrator.deps.clustering_service.cluster_chunks(
        chunks, orchestrator.config.raptor_max_clusters
    )
    assert isinstance(tree, dict)
    assert "level_0" in tree
