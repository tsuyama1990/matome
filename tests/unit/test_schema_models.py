import pytest
from pydantic import ValidationError
from domain_models.manifest import DIKWLevel, NodeMetadata, SummaryNode

def test_dikw_level_enum() -> None:
    assert DIKWLevel.WISDOM == "wisdom"
    assert DIKWLevel.KNOWLEDGE == "knowledge"
    assert DIKWLevel.INFORMATION == "information"
    assert DIKWLevel.DATA == "data"

def test_node_metadata_validation() -> None:
    # Valid
    meta = NodeMetadata(
        dikw_level=DIKWLevel.WISDOM,
        is_user_edited=True,
        refinement_history=["instruction 1"],
        cluster_id=1,
        type="test"
    )
    assert meta.dikw_level == DIKWLevel.WISDOM
    assert meta.is_user_edited is True
    assert meta.cluster_id == 1

    # Valid with defaults
    meta_default = NodeMetadata()
    assert meta_default.dikw_level is None
    assert meta_default.is_user_edited is False
    assert meta_default.refinement_history == []

    # Extra fields allowed
    meta_extra = NodeMetadata(extra_field="something")  # type: ignore[call-arg]
    # Pydantic allows access to extra fields via __getattr__ if config allows?
    # Actually, with extra="allow", fields are in __pydantic_extra__ or just attributes?
    # Let's check typical behavior. usually meta_extra.extra_field works.
    assert getattr(meta_extra, "extra_field") == "something"

def test_summary_node_with_metadata() -> None:
    # Valid
    node = SummaryNode(
        id="node1",
        text="summary",
        level=1,
        children_indices=[0],
        metadata=NodeMetadata(dikw_level=DIKWLevel.KNOWLEDGE)
    )
    assert node.metadata.dikw_level == DIKWLevel.KNOWLEDGE

    # Backward compatibility: dict input
    # Pydantic should convert dict to NodeMetadata automatically
    node_dict = SummaryNode(
        id="node2",
        text="summary",
        level=1,
        children_indices=[0],
        metadata={"dikw_level": "knowledge", "cluster_id": 10}  # type: ignore[arg-type]
    )
    assert isinstance(node_dict.metadata, NodeMetadata)
    assert node_dict.metadata.dikw_level == DIKWLevel.KNOWLEDGE
    assert node_dict.metadata.cluster_id == 10
