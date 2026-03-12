from typing import Any

import numpy as np
import pytest

from src.domain_models import GraphState, SemanticChunk
from src.domain_models.chunk import ChunkMetadata
from src.infrastructure.knowledge_graph import KnowledgeGraphServiceImpl
from src.interfaces import GraphError, LLMProtocol


class MockLLMProtocol(LLMProtocol):
    def invoke(self, prompt: str, timeout: int = 30, retries: int = 3, **kwargs: Any) -> str:
        return "TITLE: Mock Summary Title\nSUMMARY: This is a mocked dense summary of the cluster."


def test_generate_raptor_tree_single_chunk() -> None:
    service = KnowledgeGraphServiceImpl(llm_gateway=MockLLMProtocol(), random_state=42)
    chunk = SemanticChunk(id="c1", text="Only one chunk here.", metadata=ChunkMetadata())
    state = GraphState(chunks=[chunk])

    new_state = service.generate_raptor_tree(state)

    assert new_state.tree is not None
    assert len(new_state.tree.nodes) == 2

    root_id = new_state.tree.root_node_id
    root_node = new_state.tree.nodes[root_id]
    assert root_node.title == "Root Knowledge"
    assert root_node.summary == "Only one chunk here."
    assert len(root_node.children_ids) == 1

    leaf_id = root_node.children_ids[0]
    leaf_node = new_state.tree.nodes[leaf_id]
    assert leaf_node.title == "Cluster Summary"
    assert leaf_node.summary == "Only one chunk here."
    assert leaf_node.children_ids == ["c1"]


def test_generate_raptor_tree_multiple_chunks() -> None:
    service = KnowledgeGraphServiceImpl(llm_gateway=MockLLMProtocol(), random_state=42)

    # 5 chunks to ensure at least some clustering takes place
    chunks = [
        SemanticChunk(
            id=f"c{i}",
            text=f"Document text {i} about artificial intelligence and machines learning.",
            metadata=ChunkMetadata(),
        )
        for i in range(5)
    ]
    state = GraphState(chunks=chunks)

    new_state = service.generate_raptor_tree(state)

    assert new_state.error is None
    assert new_state.tree is not None

    tree = new_state.tree
    assert tree.root_node_id is not None
    assert len(tree.nodes) > 1  # Should have root + at least 1 cluster node

    root_node = tree.nodes[tree.root_node_id]
    assert root_node.title == "Mock Summary Title"
    assert root_node.summary == "This is a mocked dense summary of the cluster."
    assert len(root_node.children_ids) > 0


def test_generate_raptor_tree_missing_llm() -> None:
    # Service without LLM allows offline mock mode, so we verify _summarize_cluster returns fallback
    service = KnowledgeGraphServiceImpl(llm_gateway=None)
    title, sum_text = service._summarize_cluster(["Test"])
    assert title == "Local Cluster Summary"
    assert "offline cluster placeholder" in sum_text


def test_generate_raptor_tree_empty_chunks() -> None:
    service = KnowledgeGraphServiceImpl(llm_gateway=MockLLMProtocol(), random_state=42)
    state = GraphState(chunks=[])

    new_state = service.generate_raptor_tree(state)

    # No changes if empty chunks
    assert new_state.tree is None
    assert new_state.error is None


def test_embed_chunks_empty_and_error() -> None:
    service = KnowledgeGraphServiceImpl(llm_gateway=MockLLMProtocol(), random_state=42)
    with pytest.raises(GraphError, match="empty or uninformative"):
        service._embed_chunks([])


def test_reduce_dimensionality_error() -> None:
    service = KnowledgeGraphServiceImpl(llm_gateway=MockLLMProtocol(), random_state=42)
    # n_components larger than valid dimensions or invalid metric could cause UMAP error
    with pytest.raises(GraphError):
        # Pass something that cannot be umap'd properly
        service._reduce_dimensionality(np.zeros((10, 10)), n_components=100)


def test_cluster_embeddings_error() -> None:
    service = KnowledgeGraphServiceImpl(llm_gateway=MockLLMProtocol(), random_state=42)
    with pytest.raises(GraphError):
        # Pass something that cannot be clustered (e.g. 1D array when 2D is expected)
        service._cluster_embeddings(np.array([1, 2, 3]), n_clusters=2)


def test_summarize_cluster_llm_error() -> None:
    class FailingLLM(LLMProtocol):
        def invoke(self, prompt: str, timeout: int = 30, retries: int = 3, **kwargs: Any) -> str:
            msg = "Mocked LLM error"
            raise ValueError(msg)

    service = KnowledgeGraphServiceImpl(llm_gateway=FailingLLM(), random_state=42)
    with pytest.raises(GraphError, match="LLM summarization failed"):
        service._summarize_cluster(["text 1"])


def test_generate_raptor_tree_batch() -> None:
    service = KnowledgeGraphServiceImpl(llm_gateway=MockLLMProtocol(), random_state=42)
    state = GraphState(chunks=[])
    # currently batch just delegates
    assert service.generate_raptor_tree_batch(state).chunks == []


def test_pivot_kj() -> None:
    service = KnowledgeGraphServiceImpl(llm_gateway=MockLLMProtocol(), random_state=42)
    state = GraphState()
    assert service.pivot_kj(state) == state


def test_generate_raptor_tree_batch_empty() -> None:
    service = KnowledgeGraphServiceImpl(llm_gateway=MockLLMProtocol(), random_state=42)
    state = GraphState(chunks=[])
    assert service.generate_raptor_tree_batch(state).chunks == []


def test_generate_raptor_tree_batch_single() -> None:
    service = KnowledgeGraphServiceImpl(llm_gateway=MockLLMProtocol(), random_state=42)
    chunk = SemanticChunk(id="c1", text="Only one chunk here.", metadata=ChunkMetadata())
    state = GraphState(chunks=[chunk])
    res = service.generate_raptor_tree_batch(state)
    assert res.tree is not None


def test_generate_raptor_tree_batch_multiple() -> None:
    service = KnowledgeGraphServiceImpl(llm_gateway=MockLLMProtocol(), random_state=42)
    chunks = [
        SemanticChunk(id=f"c{i}", text=f"Document text {i} about AI.", metadata=ChunkMetadata())
        for i in range(15)
    ]
    state = GraphState(chunks=chunks)
    res = service.generate_raptor_tree_batch(state, batch_size=5)
    assert res.tree is not None
