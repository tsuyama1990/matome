import pytest
from pydantic import ValidationError

from domain_models.manifest import NodeMetadata, SummaryNode
from domain_models.types import DIKWLevel


def test_dikw_level_enum() -> None:
    """Test DIKWLevel enum values."""
    assert DIKWLevel.WISDOM.value == "wisdom"
    assert DIKWLevel.KNOWLEDGE.value == "knowledge"
    assert DIKWLevel.INFORMATION.value == "information"
    assert DIKWLevel.DATA.value == "data"


def test_node_metadata_defaults() -> None:
    """Test NodeMetadata default values."""
    meta = NodeMetadata()
    assert meta.dikw_level == DIKWLevel.DATA
    assert meta.is_user_edited is False
    assert meta.refinement_history == []


def test_node_metadata_validation() -> None:
    """Test NodeMetadata validation logic."""
    # Valid
    meta = NodeMetadata(dikw_level=DIKWLevel.WISDOM, is_user_edited=True)
    assert meta.dikw_level == DIKWLevel.WISDOM
    assert meta.is_user_edited is True

    # Invalid DIKW level
    with pytest.raises(ValidationError):
        NodeMetadata(dikw_level="invalid_level")  # type: ignore[arg-type]


def test_summary_node_with_metadata() -> None:
    """Test SummaryNode creation with NodeMetadata."""
    meta = NodeMetadata(dikw_level=DIKWLevel.KNOWLEDGE, cluster_id=123)
    node = SummaryNode(
        id="test_id",
        text="Sample summary",
        level=2,
        children_indices=[1, 2, 3],
        metadata=meta,
    )
    assert node.metadata.dikw_level == DIKWLevel.KNOWLEDGE
    assert node.metadata.cluster_id == 123


def test_summary_node_backward_compatibility() -> None:
    """Test SummaryNode creation with dict metadata (auto-converted)."""
    node = SummaryNode(
        id="test_id",
        text="Sample summary",
        level=2,
        children_indices=[1, 2, 3],
        metadata={"dikw_level": "wisdom", "extra_field": "allowed"},  # type: ignore
    )
    assert node.metadata.dikw_level == DIKWLevel.WISDOM
    # Extra fields are allowed in NodeMetadata config
    assert getattr(node.metadata, "extra_field", None) == "allowed"
