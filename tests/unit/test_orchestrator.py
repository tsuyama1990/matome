from src.domain_models import DocumentFactory
from src.infrastructure import InMemoryDocumentRepository
from src.infrastructure.orchestrator import PipelineOrchestrator
from tests.helpers.mocks import MockAIService


def test_orchestrator_chunking_fallback() -> None:
    repo = InMemoryDocumentRepository()
    ai = MockAIService()
    factory = DocumentFactory()
    orchestrator = PipelineOrchestrator(doc_repo=repo, ai_service=ai, doc_factory=factory)

    chunks = orchestrator._perform_semantic_chunking("test " * 1000)
    assert len(chunks) > 0
    assert "test" in chunks[0]

def test_orchestrator_ner_fallback() -> None:
    repo = InMemoryDocumentRepository()
    ai = MockAIService()
    factory = DocumentFactory()
    orchestrator = PipelineOrchestrator(doc_repo=repo, ai_service=ai, doc_factory=factory)

    entities = orchestrator._extract_entities(["test chunk 1", "test chunk 2"])
    # May use Spacy if present, or fallback. Ensure it returns a dictionary.
    assert isinstance(entities, dict)

def test_orchestrator_raptor_fallback() -> None:
    repo = InMemoryDocumentRepository()
    ai = MockAIService()
    factory = DocumentFactory()
    orchestrator = PipelineOrchestrator(doc_repo=repo, ai_service=ai, doc_factory=factory)

    # Pass more than 15 chunks to avoid the UMAP dimensionality error for N <= 15 when using defaults
    chunks = [f"test document chunk number {i}" for i in range(20)]
    tree = orchestrator._generate_raptor_tree(chunks)
    assert isinstance(tree, dict)
    assert "level_0" in tree
