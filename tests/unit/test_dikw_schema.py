from domain_models.data_schema import DIKWLevel, NodeMetadata


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


def test_node_metadata_custom_values() -> None:
    """Test NodeMetadata with custom values."""
    meta = NodeMetadata(
        dikw_level=DIKWLevel.WISDOM,
        is_user_edited=True,
        refinement_history=["instruction 1"],
    )
    assert meta.dikw_level == DIKWLevel.WISDOM
    assert meta.is_user_edited is True
    assert meta.refinement_history == ["instruction 1"]


def test_node_metadata_extra_fields() -> None:
    """Test that NodeMetadata allows extra fields."""
    meta = NodeMetadata(extra_field="value")
    assert meta.extra_field == "value"  # type: ignore[attr-defined]
