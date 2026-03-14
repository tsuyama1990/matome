import uuid

import pytest

from src.application import NLPModelLoadError, NLPService, PivotKJEngine, RAPTOREngine, SQ3REngine
from src.domain_models import ChunkMetadata, RaptorNode, SemanticChunk
from src.infrastructure.test_services import SafeTestLLMService


def test_nlp_service_load_success() -> None:
    # Test real loading of the lightweight model without mocking
    service = NLPService(
        model_name="en_core_web_sm", time_axis_past_words=["was"], time_axis_future_words=["will"]
    )
    assert service.nlp is not None


def test_nlp_service_load_import_error(monkeypatch: pytest.MonkeyPatch) -> None:
    import sys

    monkeypatch.delitem(sys.modules, "spacy", raising=False)
    # Actually monkeypatching sys.modules to None is how it was done:
    monkeypatch.setitem(sys.modules, "spacy", None)
    with pytest.raises(NLPModelLoadError, match="Spacy library is not installed."):
        NLPService(
            model_name="en_core_web_sm",
            time_axis_past_words=["was"],
            time_axis_future_words=["will"],
        )


def test_nlp_service_load_os_error() -> None:
    # Test error handling explicitly using a non-existent model name
    with pytest.raises(
        NLPModelLoadError, match="Spacy model 'nonexistent_model' is missing. Please install it."
    ):
        NLPService(
            model_name="nonexistent_model",
            time_axis_past_words=["was"],
            time_axis_future_words=["will"],
        )


def test_nlp_service_tag_entities() -> None:
    service = NLPService(
        model_name="en_core_web_sm", time_axis_past_words=["was"], time_axis_future_words=["will"]
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
        model_name="en_core_web_sm", time_axis_past_words=["was"], time_axis_future_words=["will"]
    )
    # Manually unset nlp attribute to simulate uninitialized state without mocking
    service.nlp = None
    with pytest.raises(RuntimeError, match="NLP model is not loaded."):
        service.tag_entities_and_axes([])


def test_nlp_service_malicious_input() -> None:
    service = NLPService(
        model_name="en_core_web_sm", time_axis_past_words=["was"], time_axis_future_words=["will"]
    )
    chunk = SemanticChunk(
        id=uuid.uuid4(),
        content="<script>alert('XSS')</script> SELECT * FROM users;",
        embedding=[0.0] * 768,
        metadata=ChunkMetadata(source_file="test.txt"),
    )
    # The NLP processor shouldn't crash, execute the script, or hallucinate random entities
    # Instead, bleach completely strips HTML out safely.
    service.tag_entities_and_axes([chunk])
    assert "script" not in chunk.metadata.extracted_entities


@pytest.mark.asyncio
async def test_raptor_engine_cluster_chunks() -> None:
    from src.infrastructure.clustering import UMAPGMMClusteringStrategy

    llm = SafeTestLLMService()
    clustering = UMAPGMMClusteringStrategy()
    engine = RAPTOREngine(llm=llm, clustering_strategy=clustering, max_levels=2, max_clusters=2)

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

    nodes = await engine.cluster_chunks(chunks)
    assert len(nodes) > 0
    assert all(isinstance(node, RaptorNode) for node in nodes)
    assert all(node.summarized_content == "Test Summary or Question." for node in nodes)


def test_raptor_engine_cluster_edge_cases() -> None:
    import numpy as np

    from src.infrastructure.clustering import UMAPGMMClusteringStrategy

    clustering = UMAPGMMClusteringStrategy()

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

    feedback = await engine.evaluate_answer("I think it is X.", node)
    assert feedback == "Test Summary or Question."


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
