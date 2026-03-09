from src.domain_models import DocumentFactory
from src.infrastructure import InMemoryDocumentRepository
from src.infrastructure.orchestrator import PipelineOrchestrator
from tests.helpers.mocks import MockAIService


def test_orchestrator_chunking_fallback() -> None:
    from pydantic import SecretStr

    from src.config import Settings

    settings = Settings(openrouter_api_key=SecretStr("sk-or-v1-validkey12345678901234567890"))
    repo = InMemoryDocumentRepository()
    ai = MockAIService()
    factory = DocumentFactory()
    orchestrator = PipelineOrchestrator(
        doc_repo=repo, ai_service=ai, doc_factory=factory, settings=settings
    )

    chunks = orchestrator.text_splitter.split_text("test " * 1000)
    assert len(chunks) > 0
    assert "test" in chunks[0]


def test_orchestrator_ner_fallback() -> None:
    from pydantic import SecretStr

    from src.config import Settings

    settings = Settings(openrouter_api_key=SecretStr("sk-or-v1-validkey12345678901234567890"))
    repo = InMemoryDocumentRepository()
    ai = MockAIService()
    factory = DocumentFactory()
    orchestrator = PipelineOrchestrator(
        doc_repo=repo, ai_service=ai, doc_factory=factory, settings=settings
    )

    entities = orchestrator.entity_extractor.extract_entities(["test chunk 1", "test chunk 2"])
    # May use Spacy if present, or fallback. Ensure it returns a dictionary.
    assert isinstance(entities, dict)


def test_orchestrator_raptor_fallback() -> None:
    from pydantic import SecretStr

    from src.config import Settings

    settings = Settings(openrouter_api_key=SecretStr("sk-or-v1-validkey12345678901234567890"))
    repo = InMemoryDocumentRepository()
    ai = MockAIService()
    factory = DocumentFactory()
    orchestrator = PipelineOrchestrator(
        doc_repo=repo, ai_service=ai, doc_factory=factory, settings=settings
    )

    # Pass more than 15 chunks to avoid the UMAP dimensionality error for N <= 15 when using defaults
    chunks = [f"test document chunk number {i}" for i in range(20)]
    tree = orchestrator.clustering_service.cluster_chunks(chunks, settings.raptor_max_clusters)
    assert isinstance(tree, dict)
    assert "level_0" in tree
