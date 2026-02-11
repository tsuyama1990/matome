import pytest
from pydantic import ValidationError

from domain_models.metadata import DIKWLevel, NodeMetadata


def test_node_metadata_valid_instantiation() -> None:
    """Test creating NodeMetadata with valid DIKW levels."""
    meta = NodeMetadata(dikw_level=DIKWLevel.WISDOM)
    assert meta.dikw_level == DIKWLevel.WISDOM
    # mypy complains about overlapping equality check for enum vs string
    assert str(meta.dikw_level) == "wisdom"
    assert not meta.is_user_edited
    assert meta.refinement_history == []


def test_node_metadata_invalid_level() -> None:
    """Test that invalid DIKW levels raise ValidationError."""
    with pytest.raises(ValidationError):
        NodeMetadata(dikw_level="magic")  # type: ignore


def test_node_metadata_defaults() -> None:
    """Test default values."""
    meta = NodeMetadata()
    assert meta.dikw_level == DIKWLevel.DATA
    assert not meta.is_user_edited


def test_node_metadata_extra_fields() -> None:
    """Test that extra fields are allowed."""
    # Using kwargs for extra fields requires type ignore in static analysis but works in Pydantic
    meta = NodeMetadata(extra_field="value")  # type: ignore
    assert meta.extra_field == "value"  # type: ignore

    # Using dict unpacking
    meta2 = NodeMetadata(unknown=123)  # type: ignore
    assert meta2.unknown == 123  # type: ignore
