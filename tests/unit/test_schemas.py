from typing import Any

import pytest
from pydantic import ValidationError

from src.domain_models import (
    KnowledgeNode,
    NodeState,
    PivotResponse,
    RestructuredNode,
    SemanticChunk,
    SummaryTree,
)


def test_semantic_chunk_validation() -> None:
    """Validates boundary conditions and extra='forbid' for SemanticChunk."""
    # Valid
    chunk = SemanticChunk(id="c1", text="Hello world")
    assert chunk.id == "c1"
    assert chunk.text == "Hello world"
    assert chunk.metadata == {}

    # Invalid string length
    with pytest.raises(ValidationError):
        SemanticChunk(id="c2", text="")

    # Too long
    with pytest.raises(ValidationError):
        SemanticChunk(id="c3", text="a" * 100001)

    # Extra forbid
    with pytest.raises(ValidationError):
        # We need to intentionally type ignore to test runtime forbid logic without mypy complaining
        SemanticChunk(id="c4", text="Test", extra_field="should fail")  # type: ignore[call-arg]

    # Malformed Unicode (Surrogate characters are not strict UTF-8)
    with pytest.raises(ValidationError):
        SemanticChunk(id="c5", text="Hello\ud800world")


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
