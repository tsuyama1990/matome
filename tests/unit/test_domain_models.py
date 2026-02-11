from typing import Any

import pytest
from pydantic import ValidationError

from domain_models.manifest import SummaryNode
from domain_models.metadata import DIKWLevel, NodeMetadata


def test_summary_node_creation() -> None:
    node = SummaryNode(
        id="123",
        text="Sample summary",
        level=1,
        children_indices=[0, 1],
        metadata=NodeMetadata(dikw_level=DIKWLevel.WISDOM)
    )
    assert node.id == "123"
    assert node.level == 1
    assert node.metadata.dikw_level == DIKWLevel.WISDOM


def test_summary_node_creation_with_dict() -> None:
    """Test that a dictionary passed to metadata is converted to NodeMetadata."""
    data: dict[str, Any] = {
        "id": "123",
        "text": "Sample summary",
        "level": 1,
        "children_indices": [0, 1],
        "metadata": {"dikw_level": "knowledge", "extra": "value"}
    }
    # This relies on the pre-validator in SummaryNode
    node = SummaryNode(**data)
    assert isinstance(node.metadata, NodeMetadata)
    assert node.metadata.dikw_level == DIKWLevel.KNOWLEDGE
    assert node.metadata.extra == "value" # type: ignore[attr-defined]


def test_summary_node_validation_error() -> None:
    with pytest.raises(ValidationError):
        SummaryNode(
            id="123",
            text="Sample summary",
            level=0, # Invalid level (ge=1)
            children_indices=[0, 1]
        )
