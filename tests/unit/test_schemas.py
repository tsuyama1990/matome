from typing import Any

import pytest
from pydantic import ValidationError

from src.domain_models import (
    GraphState,
    KnowledgeNode,
    NodeState,
    PivotResponse,
    RestructuredNode,
    SemanticChunk,
    SummaryTree,
)
from src.domain_models.constants import DEFAULT_MAX_CHUNK_SCAN_SIZE


def test_semantic_chunk_validation() -> None:
    """Validates boundary conditions and extra='forbid' for SemanticChunk."""
    # Valid
    chunk = SemanticChunk(id="c1", text="Hello world")
    assert chunk.id == "c1"
    assert chunk.text == "Hello world"
    assert chunk.metadata.page_number == 1
    assert chunk.metadata.source_document == "unknown"

    # Invalid string length
    with pytest.raises(ValidationError):
        SemanticChunk(id="c2", text="")

    # Too long (Cycle 3 ReDoS protection via bounded quantifiers)
    with pytest.raises(ValidationError, match="String should have at most"):
        SemanticChunk(id="c3", text="a" * (DEFAULT_MAX_CHUNK_SCAN_SIZE + 1))

    # Extra forbid
    with pytest.raises(ValidationError):
        # We need to intentionally type ignore to test runtime forbid logic without mypy complaining
        SemanticChunk(id="c4", text="Test", extra_field="should fail")  # type: ignore[call-arg]

    # Malformed Unicode (Surrogate characters are not strict UTF-8)
    with pytest.raises(ValidationError):
        SemanticChunk(id="c5", text="Hello\ud800world")

    # Test strict metadata typing
    invalid_metadata: dict[str, Any] = {"page_number": -1}
    with pytest.raises(ValidationError):
        SemanticChunk(id="c6", text="Valid", metadata=invalid_metadata)  # type: ignore[arg-type]


def test_knowledge_node_validation() -> None:
    """Validates boundary conditions and extra='forbid' for KnowledgeNode."""
    # Valid
    node = KnowledgeNode(id="n1", title="Chapter 1", summary="A long time ago")
    assert node.state == NodeState.LOCKED
    assert node.children_ids == []

    # Valid unlocked
    unlocked_node = KnowledgeNode(id="n2", title="Chap 2", summary="Foo", state=NodeState.UNLOCKED)
    assert unlocked_node.state == NodeState.UNLOCKED

    # Invalid state
    # We test that invalid enum values raise validation errors properly
    invalid_data: dict[str, Any] = {
        "id": "n3",
        "title": "Chap 3",
        "summary": "Bar",
        "state": "Pending",
    }
    with pytest.raises(ValidationError):
        KnowledgeNode(**invalid_data)


def test_summary_tree_validation() -> None:
    """Validates boundary conditions and extra='forbid' for SummaryTree."""
    node = KnowledgeNode(id="n1", title="Chapter 1", summary="A long time ago")

    # Valid
    tree = SummaryTree(root_node_id="n1", nodes={"n1": node})
    assert tree.root_node_id == "n1"
    assert "n1" in tree.nodes


def test_pivot_response_validation() -> None:
    """Validates boundary conditions and extra='forbid' for PivotResponse."""
    # Valid
    restructured_node = RestructuredNode(id="n1", title="Title", position_data={"position": "past"})
    response = PivotResponse(
        axis="Time", restructured_nodes=[restructured_node], mermaid_diagram="graph TD; A-->B;"
    )
    assert response.axis == "Time"
    assert response.restructured_nodes[0].id == "n1"

    # Missing diagram
    # We use Any typing on dict definition to verify validation safely without typing complaining
    invalid_data: dict[str, Any] = {
        "axis": "Time",
        "restructured_nodes": [
            {"id": "n1", "title": "Title", "position_data": {"position": "past"}}
        ],
    }
    with pytest.raises(ValidationError):
        PivotResponse(**invalid_data)


def test_graph_state_validation() -> None:
    """Validates that GraphState enforces strict state typing and extra='forbid'."""
    # Valid initialization
    state = GraphState(
        file_path="foo.txt",
        raw_text="raw test",
        cleaned_text="clean test",
        embedded_chunks=True,
    )
    assert state.file_path == "foo.txt"
    assert state.raw_text == "raw test"
    assert state.cleaned_text == "clean test"
    assert state.embedded_chunks is True
    assert state.chunks == []
    assert state.tree is None
    assert state.active_node_id is None
    assert state.pivot_axis is None
    assert state.pivot_response is None
    assert state.error is None

    # Invalid initialization (extra field)
    with pytest.raises(ValidationError):
        GraphState(file_path="foo.txt", invalid_field="this should fail")  # type: ignore[call-arg]
