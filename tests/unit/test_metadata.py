import pytest
from pydantic import ValidationError

from domain_models.manifest import SummaryNode
from domain_models.metadata import DIKWLevel, NodeMetadata


def test_dikw_level_enum() -> None:
    assert DIKWLevel.WISDOM == "wisdom"
    assert DIKWLevel.KNOWLEDGE == "knowledge"
    assert DIKWLevel.INFORMATION == "information"
    assert DIKWLevel.DATA == "data"


def test_node_metadata_defaults() -> None:
    meta = NodeMetadata()
    assert meta.dikw_level is None
    assert meta.is_user_edited is False
    assert meta.prompt_history == []
    assert meta.cluster_id is None
    assert meta.source_chunk_indices is None


def test_node_metadata_validation() -> None:
    meta = NodeMetadata(dikw_level=DIKWLevel.WISDOM, is_user_edited=True)
    assert meta.dikw_level == DIKWLevel.WISDOM
    assert meta.is_user_edited is True

    # Invalid DIKW level
    with pytest.raises(ValidationError):
        NodeMetadata(dikw_level="invalid")  # type: ignore[arg-type]


def test_node_metadata_extra_fields() -> None:
    # Should allow extra fields
    meta = NodeMetadata(dikw_level=DIKWLevel.DATA, extra_field="test")  # type: ignore[call-arg]
    assert meta.dikw_level == DIKWLevel.DATA
    assert getattr(meta, "extra_field") == "test"


def test_summary_node_integration() -> None:
    # Test that SummaryNode accepts dict and converts to NodeMetadata
    node = SummaryNode(
        id="test_id",
        text="summary text",
        level=1,
        children_indices=["1", "2"],
        metadata={"dikw_level": "wisdom", "extra": 123},  # type: ignore[arg-type]
    )
    assert isinstance(node.metadata, NodeMetadata)
    assert node.metadata.dikw_level == DIKWLevel.WISDOM
    assert getattr(node.metadata, "extra") == 123
