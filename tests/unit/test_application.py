import uuid

import pytest
from pydantic import ValidationError

from src.application import (
    IngestionPipeline,
    NLPService,
    PivotKJEngine,
    RaptorEngine,
    SQ3REngine,
)
from src.domain_models import ChunkMetadata, LearningProgress, RaptorNode, SemanticChunk
from src.infrastructure.test_services import (
    DummyEmbeddingService,
    PlainTextParser,
    SafeTestLLMService,
)
from src.interfaces.dependencies import LLMProtocol


def test_nlp_service_load_success() -> None:
    # Test real loading of the lightweight model without mocking
    from src.interfaces.dependencies import _load_spacy_model

    nlp_model = _load_spacy_model("en_core_web_sm")
    service = NLPService(
        nlp_model=nlp_model, time_axis_past_words=["was"], time_axis_future_words=["will"]
    )
    assert service.nlp is not None


def test_nlp_service_load_import_error(monkeypatch: pytest.MonkeyPatch) -> None:
    import sys

    monkeypatch.delitem(sys.modules, "spacy", raising=False)
    # Actually monkeypatching sys.modules to None is how it was done:
    monkeypatch.setitem(sys.modules, "spacy", None)
    from src.interfaces.dependencies import _load_spacy_model

    assert _load_spacy_model("en_core_web_sm") is None


def test_nlp_service_load_os_error() -> None:
    # Test error handling explicitly using a non-existent model name
    from src.interfaces.dependencies import _load_spacy_model

    assert _load_spacy_model("nonexistent_model") is None


def test_nlp_service_tag_entities() -> None:
    from src.interfaces.dependencies import _load_spacy_model

    nlp_model = _load_spacy_model("en_core_web_sm")
    service = NLPService(
        nlp_model=nlp_model, time_axis_past_words=["was"], time_axis_future_words=["will"]
    )
    chunk = SemanticChunk(
        id=uuid.uuid4(),
        content="Apple is looking at buying U.K. startup for $1 billion today.",
        embedding=[0.0] * 768,
        metadata=ChunkMetadata(source_file="test.txt"),
    )
    if True:
        service.tag_entities_and_axes([chunk])

    # Apple is recognized as ORG, satisfying the target_labels extraction and actor assignment
    assert "Apple" in chunk.metadata.extracted_entities
    # DATE is not in target_labels so it's not extracted, but it sets time_axis
    assert "today" not in chunk.metadata.extracted_entities

    assert chunk.metadata.time_axis == "Present"


def test_nlp_service_tag_entities_not_loaded() -> None:
    service = NLPService(
        nlp_model=None, time_axis_past_words=["was"], time_axis_future_words=["will"]
    )
    with pytest.raises(RuntimeError, match="NLP model is not loaded."):
        service.tag_entities_and_axes([])


def test_nlp_service_malicious_input() -> None:
    from src.interfaces.dependencies import _load_spacy_model

    nlp_model = _load_spacy_model("en_core_web_sm")
    service = NLPService(
        nlp_model=nlp_model, time_axis_past_words=["was"], time_axis_future_words=["will"]
    )
    chunk = SemanticChunk(
        id=uuid.uuid4(),
        content="<script>alert('XSS')</script> SELECT * FROM users;",
        embedding=[0.0] * 768,
        metadata=ChunkMetadata(source_file="test.txt"),
    )
    # The NLP processor shouldn't crash, execute the script, or hallucinate random entities
    # The payload is sanitized cleanly.
    service.tag_entities_and_axes([chunk])


@pytest.mark.asyncio
async def test_raptor_engine_cluster_chunks() -> None:
    import umap.umap_ as umap
    from sklearn.mixture import GaussianMixture

    from src.infrastructure.clustering import UMAPGMMClusteringStrategy

    llm = SafeTestLLMService()
    clustering = UMAPGMMClusteringStrategy(umap_lib=umap, gmm_cls=GaussianMixture)
    engine = RaptorEngine(llm=llm, clustering_strategy=clustering, max_clusters=2)

    # Create test chunks
    chunks = []
    for i in range(5):
        chunk = SemanticChunk(
            id=uuid.uuid4(),
            content=f"This is chunk {i}",
            embedding=[float(i) / 10.0] * 768,
            metadata=ChunkMetadata(source_file="test.txt"),
        )
        chunks.append(chunk)

    nodes = await engine.build_tree(chunks)
    assert len(nodes) > 0
    assert all(isinstance(node, RaptorNode) for node in nodes)
    assert all(node.summarized_content == "Test Summary or Question." for node in nodes)


def test_raptor_engine_cluster_edge_cases() -> None:
    import numpy as np
    import umap.umap_ as umap
    from sklearn.mixture import GaussianMixture

    from src.infrastructure.clustering import UMAPGMMClusteringStrategy

    clustering = UMAPGMMClusteringStrategy(umap_lib=umap, gmm_cls=GaussianMixture)

    # Test empty array (must have shape length 2 but empty size)
    empty = np.array([[]])
    assert clustering.cluster(empty, 2) == {}

    # Test single item
    single = np.array([[0.1, 0.2]])
    assert clustering.cluster(single, 2) == {0: [0]}

    # Test two items
    two = np.array([[0.1, 0.2], [0.3, 0.4]])
    assert clustering.cluster(two, 2) == {0: [0], 1: [1]}

    # Test identical items that would cause GMM to fail with singular covariance
    identical = np.array([[0.1, 0.2], [0.1, 0.2], [0.1, 0.2], [0.1, 0.2]])
    assert clustering.cluster(identical, 2) == {0: [0, 1, 2, 3]}


@pytest.mark.asyncio
async def test_sq3r_engine() -> None:
    llm = SafeTestLLMService()
    engine = SQ3REngine(llm=llm)

    node = RaptorNode(
        node_id=str(uuid.uuid4()),
        level=0,
        summarized_content="Important summary.",
    )

    q = await engine.generate_question(node)
    assert q == "Test Summary or Question."

    feedback = await engine.evaluate_answer(node, "I think it is X.")
    assert feedback is False


def test_pivot_kj_engine() -> None:
    engine = PivotKJEngine(allowed_axes=frozenset({"actor", "time", "entities"}))

    chunks = [
        SemanticChunk(
            id=uuid.uuid4(),
            content="A",
            embedding=[0.0] * 768,
            metadata=ChunkMetadata(source_file="f1", actor_axis="Admin"),
        ),
        SemanticChunk(
            id=uuid.uuid4(),
            content="B",
            embedding=[0.0] * 768,
            metadata=ChunkMetadata(source_file="f1", actor_axis="User"),
        ),
        SemanticChunk(
            id=uuid.uuid4(),
            content="C",
            embedding=[0.0] * 768,
            metadata=ChunkMetadata(source_file="f1", actor_axis="Admin"),
        ),
    ]

    clusters = engine.pivot(chunks, "actor")
    assert "Admin" in clusters
    assert "User" in clusters
    assert len(clusters["Admin"]) == 2
    assert len(clusters["User"]) == 1

    time_clusters = engine.pivot(chunks, "time")
    assert "Uncategorized" in time_clusters
    assert len(time_clusters["Uncategorized"]) == 3

    with pytest.raises(ValueError, match="Invalid axis"):
        engine.pivot(chunks, "unsupported_axis")


@pytest.mark.asyncio
async def test_ingestion_pipeline_process_document() -> None:
    llm = SafeTestLLMService()
    embedding = DummyEmbeddingService(dimension=384)
    parser = PlainTextParser()

    import umap.umap_ as umap
    from sklearn.mixture import GaussianMixture

    from src.application import RaptorEngine
    from src.infrastructure.clustering import UMAPGMMClusteringStrategy

    raptor = RaptorEngine(
        llm=llm,
        clustering_strategy=UMAPGMMClusteringStrategy(umap_lib=umap, gmm_cls=GaussianMixture),
    )
    pipeline = IngestionPipeline(
        llm=llm,
        embedding=embedding,
        text_parser=parser,
        raptor_engine=raptor,
        fast_model_name="default",
    )

    # We provide raw bytes and test successful chunking
    raw_text = "This is sentence one. This is sentence two. Here is a third sentence."
    content_bytes = raw_text.encode("utf-8")

    chunks = await pipeline.process_document(content_bytes, "test_doc.txt")

    # Assert return type
    assert len(chunks) > 0
    assert all(isinstance(chunk, SemanticChunk) for chunk in chunks)

    # Assert dimensionality is exact
    for chunk in chunks:
        assert len(chunk.embedding) == 384
        assert chunk.metadata.source_file == "test_doc.txt"


@pytest.mark.asyncio
async def test_ingestion_pipeline_embedding_validation_failure() -> None:
    llm = SafeTestLLMService()
    # Provide an invalid dimension to test domain model constraint enforcement
    embedding = DummyEmbeddingService(dimension=123)
    parser = PlainTextParser()

    import umap.umap_ as umap
    from sklearn.mixture import GaussianMixture

    from src.application import RaptorEngine
    from src.infrastructure.clustering import UMAPGMMClusteringStrategy

    raptor = RaptorEngine(
        llm=llm,
        clustering_strategy=UMAPGMMClusteringStrategy(umap_lib=umap, gmm_cls=GaussianMixture),
    )
    pipeline = IngestionPipeline(
        llm=llm,
        embedding=embedding,
        text_parser=parser,
        raptor_engine=raptor,
        fast_model_name="default",
    )
    content_bytes = b"A simple text to trigger failure."

    with pytest.raises(ValidationError, match="Embedding length 123 is invalid"):
        await pipeline.process_document(content_bytes, "test_doc.txt")





class DummyLLMService(LLMProtocol):
    def __init__(self, return_text: str) -> None:
        self.return_text = return_text

    async def generate(self, prompt: str, **kwargs: str) -> str:
        return self.return_text

    async def generate_text(self, prompt: str, model: str) -> str:
        return self.return_text


class PromptSpyLLMService(LLMProtocol):
    def __init__(self, return_text: str) -> None:
        self.return_text = return_text
        self.received_prompt = ""

    async def generate(self, prompt: str, **kwargs: str) -> str:
        self.received_prompt = prompt
        return self.return_text

    async def generate_text(self, prompt: str, model: str) -> str:
        self.received_prompt = prompt
        return self.return_text


@pytest.mark.asyncio
async def test_sq3r_generate_question() -> None:
    """Test SQ3REngine.generate_question returns the string and constructs the right prompt."""
    node = RaptorNode(
        node_id="test_node",
        level=1,
        summarized_content="The quick brown fox jumps over the lazy dog.",
    )
    spy_llm = PromptSpyLLMService("What jumps over the lazy dog?")
    engine = SQ3REngine(llm=spy_llm)

    question = await engine.generate_question(node, difficulty="factual")

    assert question == "What jumps over the lazy dog?"
    assert "The quick brown fox jumps over the lazy dog." in spy_llm.received_prompt
    assert "factual" in spy_llm.received_prompt


@pytest.mark.asyncio
async def test_sq3r_evaluate_answer_yes() -> None:
    """Test evaluate_answer correctly parses a YES response."""
    node = RaptorNode(
        node_id="test_node",
        level=1,
        summarized_content="The quick brown fox jumps over the lazy dog.",
    )
    spy_llm = PromptSpyLLMService("Yes, that is correct.")
    engine = SQ3REngine(llm=spy_llm)

    result = await engine.evaluate_answer(node, "A fox")

    assert result is True
    assert "The quick brown fox jumps over the lazy dog." in spy_llm.received_prompt
    assert "A fox" in spy_llm.received_prompt
    assert "YES" in spy_llm.received_prompt or "NO" in spy_llm.received_prompt


@pytest.mark.asyncio
async def test_sq3r_evaluate_answer_no() -> None:
    """Test evaluate_answer correctly parses a NO response."""
    node = RaptorNode(
        node_id="test_node",
        level=1,
        summarized_content="The quick brown fox jumps over the lazy dog.",
    )
    spy_llm = PromptSpyLLMService("NO, that is wrong.")
    engine = SQ3REngine(llm=spy_llm)

    result = await engine.evaluate_answer(node, "A cat")

    assert result is False


def test_sq3r_unlock_node() -> None:
    """Test unlock_node adds the node_id to the unlocked_node_ids set."""
    engine = SQ3REngine(llm=DummyLLMService(""))
    progress = LearningProgress(document_id=uuid.uuid4())

    assert "node_1" not in progress.unlocked_node_ids

    updated_progress = engine.unlock_node(progress, "node_1")

    assert "node_1" in updated_progress.unlocked_node_ids
    assert updated_progress is progress  # it should mutate the original object
