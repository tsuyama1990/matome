import pytest
from pydantic import ValidationError

from domain_models.manifest import NodeMetadata, SummaryNode
from domain_models.types import DIKWLevel


def test_dikw_level_enum():
    """Test that DIKWLevel enum has correct values."""
    assert DIKWLevel.WISDOM == "wisdom"
    assert DIKWLevel.KNOWLEDGE == "knowledge"
    assert DIKWLevel.INFORMATION == "information"
    assert DIKWLevel.DATA == "data"


def test_node_metadata_defaults():
    """Test default values for NodeMetadata."""
    meta = NodeMetadata()
    assert meta.dikw_level == DIKWLevel.DATA
    assert meta.is_user_edited is False
    assert meta.refinement_history == []
    assert meta.cluster_id is None
    assert meta.type is None


def test_node_metadata_validation():
    """Test strict validation for NodeMetadata."""
    # Valid input
    meta = NodeMetadata(dikw_level=DIKWLevel.WISDOM, is_user_edited=True)
    assert meta.dikw_level == DIKWLevel.WISDOM
    assert meta.is_user_edited is True

    # Invalid DIKW level
    with pytest.raises(ValidationError):
        NodeMetadata(dikw_level="magic")

    # Extra fields (should be forbidden)
    with pytest.raises(ValidationError):
        NodeMetadata(extra_field="fail")


def test_summary_node_with_metadata():
    """Test SummaryNode creation with typed metadata."""
    meta = NodeMetadata(dikw_level=DIKWLevel.KNOWLEDGE, cluster_id="cluster-123")
    node = SummaryNode(
        id="node-1",
        text="Summary text",
        level=2,
        children_indices=[1, 2],
        metadata=meta,
    )
    assert node.metadata.dikw_level == DIKWLevel.KNOWLEDGE
    assert node.metadata.cluster_id == "cluster-123"

    # Test dict compatibility (Pydantic converts dict to model if compatible)
    node_from_dict = SummaryNode(
        id="node-2",
        text="Summary text",
        level=1,
        children_indices=[3],
        metadata={"dikw_level": "information", "cluster_id": 456},
    )
    assert node_from_dict.metadata.dikw_level == DIKWLevel.INFORMATION
    assert node_from_dict.metadata.cluster_id == 456
