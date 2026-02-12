import pytest

from domain_models.data_schema import DIKWLevel, NodeMetadata
from domain_models.manifest import SummaryNode


def test_node_metadata_defaults() -> None:
    meta = NodeMetadata()
    assert meta.dikw_level == DIKWLevel.DATA
    assert meta.is_user_edited is False
    assert meta.refinement_history == []
    assert meta.cluster_id is None
    assert meta.type is None

def test_node_metadata_dict_compatibility() -> None:
    # Simulate loading from old dict with extra fields
    old_data = {"cluster_id": 123, "random_key": "value"}
    meta = NodeMetadata(**old_data)  # type: ignore[arg-type]
    assert meta.cluster_id == 123
    assert meta.dikw_level == DIKWLevel.DATA
    # With extra='ignore', random_key should be discarded without error
    # verifying that legacy databases load without crashing.
    assert meta.model_extra is None

def test_node_metadata_validation() -> None:
    with pytest.raises(ValueError):
        NodeMetadata(dikw_level="invalid_level")  # type: ignore[arg-type]

def test_summary_node_integration() -> None:
    # Pydantic V2 automatically coerces dict to model if type is Model
    node = SummaryNode(
        id="test",
        text="summary",
        level=1,
        children_indices=[1],
        metadata={"cluster_id": 99} # type: ignore[arg-type]
    )
    assert isinstance(node.metadata, NodeMetadata)
    assert node.metadata.cluster_id == 99
