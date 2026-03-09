from pydantic import SecretStr

from src.config import Settings
from src.domain_models import DocumentFactory
from src.infrastructure import InMemoryDocumentRepository
from src.infrastructure.orchestrator import PipelineOrchestrator
from src.infrastructure.services import (
    DefaultClusteringService,
    DefaultEntityExtractor,
    DefaultTextSplitter,
)
from tests.helpers.mocks import MockAIService


def _create_orchestrator() -> PipelineOrchestrator:
    settings = Settings(openrouter_api_key=SecretStr("sk-or-v1-validkey12345678901234567890"))
    repo = InMemoryDocumentRepository()
    ai = MockAIService()
    factory = DocumentFactory()
    text_splitter = DefaultTextSplitter(settings=settings)
    entity_extractor = DefaultEntityExtractor()
    clustering_service = DefaultClusteringService()

    return PipelineOrchestrator(
        doc_repo=repo,
        ai_service=ai,
        doc_factory=factory,
        text_splitter=text_splitter,
        entity_extractor=entity_extractor,
        clustering_service=clustering_service,
        settings=settings,
    )


def test_orchestrator_chunking_fallback() -> None:
    orchestrator = _create_orchestrator()
    chunks = orchestrator.text_splitter.split_text("test " * 1000)
    assert len(chunks) > 0
    assert "test" in chunks[0]


def test_orchestrator_ner_fallback() -> None:
    orchestrator = _create_orchestrator()
    entities = orchestrator.entity_extractor.extract_entities(["test chunk 1", "test chunk 2"])
    # May use Spacy if present, or fallback. Ensure it returns a dictionary.
    assert isinstance(entities, dict)


def test_orchestrator_raptor_fallback() -> None:
    orchestrator = _create_orchestrator()
    # Pass more than 15 chunks to avoid the UMAP dimensionality error for N <= 15 when using defaults
    chunks = [f"test document chunk number {i}" for i in range(20)]
    tree = orchestrator.clustering_service.cluster_chunks(
        chunks, orchestrator.settings.raptor_max_clusters
    )
    assert isinstance(tree, dict)
    assert "level_0" in tree
