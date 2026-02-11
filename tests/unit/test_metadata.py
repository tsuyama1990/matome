import pytest
from pydantic import ValidationError

from domain_models.metadata import DIKWLevel, NodeMetadata


def test_node_metadata_defaults() -> None:
    meta = NodeMetadata()
    assert meta.dikw_level == DIKWLevel.DATA
    assert meta.is_user_edited is False
    assert meta.refinement_history == []


def test_node_metadata_validation() -> None:
    meta = NodeMetadata(dikw_level=DIKWLevel.WISDOM)
    assert meta.dikw_level == DIKWLevel.WISDOM

    with pytest.raises(ValidationError):
        NodeMetadata(dikw_level="invalid_level")  # type: ignore[arg-type]


def test_node_metadata_extra_fields() -> None:
    meta = NodeMetadata(extra_field="some_value")  # type: ignore[call-arg]
    assert meta.dikw_level == DIKWLevel.DATA
    assert meta.extra_field == "some_value"


def test_node_metadata_from_dict() -> None:
    data = {"dikw_level": "knowledge", "is_user_edited": True}
    meta = NodeMetadata(**data)
    assert meta.dikw_level == DIKWLevel.KNOWLEDGE
    assert meta.is_user_edited is True
