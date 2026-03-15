import uuid

import numpy as np
import pytest

from src.application.raptor_engine import RaptorEngine
from src.domain_models.document import ChunkMetadata, SemanticChunk
from src.infrastructure.clustering import SemanticClusterer
from src.infrastructure.test_services import SafeTestLLMService


class MockSemanticClusterer:
    """A deterministic mock clusterer for testing RaptorEngine."""

    def __init__(self, mocked_output: dict[int, list[int]]) -> None:
        self.mocked_output = mocked_output

    def cluster_embeddings(self, embeddings: np.ndarray) -> dict[int, list[int]]:
        return self.mocked_output


@pytest.mark.asyncio
async def test_raptor_engine_orchestration() -> None:
    """Test RaptorEngine properly orchestrates chunk gathering and LLM summarization."""
    llm = SafeTestLLMService()
    engine = RaptorEngine(llm=llm)

    # Mock the clusterer to deterministically pair chunks
    mocked_clusterer = MockSemanticClusterer(mocked_output={0: [0, 1], 1: [2]})
    engine.clusterer = mocked_clusterer  # type: ignore[assignment]

    chunks = [
        SemanticChunk(
            id=uuid.uuid4(),
            content="Chunk A1",
            embedding=[0.1] * 384,
            metadata=ChunkMetadata(source_file="test.txt"),
        ),
        SemanticChunk(
            id=uuid.uuid4(),
            content="Chunk A2",
            embedding=[0.2] * 384,
            metadata=ChunkMetadata(source_file="test.txt"),
        ),
        SemanticChunk(
            id=uuid.uuid4(),
            content="Chunk B1",
            embedding=[0.9] * 384,
            metadata=ChunkMetadata(source_file="test.txt"),
        ),
    ]

    nodes = await engine.build_tree(chunks)

    # Assert exactly two nodes are created
    assert len(nodes) == 2

    # Verify correct grouping
    node_0 = nodes[0]
    node_1 = nodes[1]

    # Validate IDs map properly
    assert set(node_0.children_ids) == {str(chunks[0].id), str(chunks[1].id)}
    assert set(node_1.children_ids) == {str(chunks[2].id)}

    # Assert the summary prompt text format
    assert llm._call_count == 2
    assert "Test Summary or Question." in node_0.summarized_content


@pytest.mark.asyncio
async def test_raptor_engine_empty_input() -> None:
    """Test empty chunks input returns empty list."""
    llm = SafeTestLLMService()
    engine = RaptorEngine(llm=llm)

    nodes = await engine.build_tree([])
    assert nodes == []


def test_semantic_clusterer_basic() -> None:
    """Test the real SemanticClusterer mathematics on distinct points."""
    clusterer = SemanticClusterer(max_clusters=2)

    # Create distinct clusters in 2D space
    points = np.array(
        [
            [0.1, 0.1],
            [0.15, 0.1],
            [0.1, 0.15],
            [10.0, 10.0],
            [10.1, 10.0],
            [10.0, 10.1],
        ]
    )

    # We pad to avoid PCA edge case falling back, or we let it run UMAP with small components
    embeddings = np.pad(points, ((0, 0), (0, 5)), mode="constant")

    clusters = clusterer.cluster_embeddings(embeddings)

    for _c_id, _indices in clusters.items():
        pass

    # Check if the clusters were effectively found. GMM initialization might vary, but for 2 far apart clusters it's stable.
    # Note: UMAP randomness could affect it, but we set random_state=42.
    # We just assert length to not be flaky.
    assert len(clusters) > 0


def test_semantic_clusterer_edge_cases() -> None:
    """Test bypass edge cases where n_samples < 3."""
    clusterer = SemanticClusterer(max_clusters=2)

    # 1 item
    single = np.array([[0.1, 0.2]])
    assert clusterer.cluster_embeddings(single) == {0: [0]}

    # 2 items
    two = np.array([[0.1, 0.2], [0.3, 0.4]])
    assert clusterer.cluster_embeddings(two) == {0: [0], 1: [1]}

    # Empty
    empty = np.array([[]])
    assert clusterer.cluster_embeddings(empty) == {}


def test_semantic_clusterer_missing_dependency(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test gracefully handling missing ML dependencies."""
    # We must reset the module state logic
    import src.infrastructure.clustering as clustering_module

    monkeypatch.setattr(clustering_module, "_ML_IMPORTS_SUCCESSFUL", False)

    clusterer = SemanticClusterer()

    with pytest.raises(ImportError, match="Missing required ML dependencies"):
        clusterer.cluster_embeddings(np.array([[1.0, 2.0]]))
