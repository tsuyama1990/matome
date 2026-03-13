import uuid
from unittest import mock

import pytest

from src.application import NLPModelLoadError, NLPService, PivotKJEngine, RAPTOREngine, SQ3REngine
from src.domain_models import ChunkMetadata, RaptorNode, SemanticChunk


def test_nlp_service_load_success() -> None:
    with mock.patch("spacy.load") as mock_load:
        mock_load.return_value = mock.MagicMock()
        service = NLPService()
        assert service.nlp is not None


def test_nlp_service_load_import_error() -> None:
    with (
        mock.patch.dict("sys.modules", {"spacy": None}),
        pytest.raises(NLPModelLoadError, match="Spacy library is not installed."),
    ):
        NLPService()


def test_nlp_service_load_os_error() -> None:
    with (
        mock.patch("spacy.load", side_effect=OSError("model not found")),
        pytest.raises(
            NLPModelLoadError, match="Spacy model 'en_core_web_sm' is missing. Please install it."
        ),
    ):
        NLPService()


def test_nlp_service_tag_entities() -> None:
    service = NLPService()
    chunk = SemanticChunk(
        id=uuid.uuid4(),
        content="Apple is looking at buying U.K. startup for $1 billion today.",
        embedding=[0.0] * 768,
        metadata=ChunkMetadata(source_file="test.txt"),
    )
    service.tag_entities_and_axes([chunk])

    # Apple is recognized as ORG, satisfying the target_labels extraction and actor assignment
    assert "Apple" in chunk.metadata.extracted_entities
    # DATE is not in target_labels so it's not extracted, but it sets time_axis
    assert "today" not in chunk.metadata.extracted_entities

    assert chunk.metadata.time_axis == "Present"


def test_nlp_service_tag_entities_not_loaded() -> None:
    with mock.patch("spacy.load") as mock_load:
        mock_load.return_value = mock.MagicMock()
        service = NLPService()
        service.nlp = None
        with pytest.raises(RuntimeError, match="NLP model is not loaded."):
            service.tag_entities_and_axes([])


def test_nlp_service_malicious_input() -> None:
    service = NLPService()
    chunk = SemanticChunk(
        id=uuid.uuid4(),
        content="<script>alert('XSS')</script> SELECT * FROM users;",
        embedding=[0.0] * 768,
        metadata=ChunkMetadata(source_file="test.txt"),
    )
    # The NLP processor shouldn't crash, execute the script, or hallucinate random entities
    service.tag_entities_and_axes([chunk])
    assert "script" not in chunk.metadata.extracted_entities


class DummyLLM:
    async def generate(self, prompt: str) -> str:
        return "Dummy Summary or Question."


@pytest.mark.asyncio
async def test_raptor_engine_cluster_chunks() -> None:
    from src.infrastructure.clustering import UMAPGMMClusteringStrategy

    llm = DummyLLM()
    clustering = UMAPGMMClusteringStrategy()
    engine = RAPTOREngine(llm=llm, clustering_strategy=clustering, max_levels=2, max_clusters=2)

    # Create dummy chunks
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
    assert all(node.summarized_content == "Dummy Summary or Question." for node in nodes)


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
    llm = DummyLLM()
    engine = SQ3REngine(llm=llm)

    node = RaptorNode(
        node_id=str(uuid.uuid4()),
        level=0,
        summarized_content="Important summary.",
    )

    q = await engine.generate_question(node)
    assert q == "Dummy Summary or Question."

    feedback = await engine.evaluate_answer("I think it is X.", node)
    assert feedback == "Dummy Summary or Question."


def test_pivot_kj_engine() -> None:
    engine = PivotKJEngine()

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
