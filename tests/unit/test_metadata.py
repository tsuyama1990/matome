from typing import Any

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
    # Use explicit argument if possible, or ignore if using extra kwargs that are dynamic
    # Pydantic allows kwargs for extra fields
    meta = NodeMetadata(extra_field="some_value")  # type: ignore[call-arg]
    assert meta.dikw_level == DIKWLevel.DATA
    # Mypy doesn't know about extra_field, use getattr
    assert meta.extra_field == "some_value" # type: ignore[attr-defined]


def test_node_metadata_from_dict() -> None:
    # Explicitly cast to Any to avoid mypy complaining about dict[str, object] unpacking
    data: dict[str, Any] = {"dikw_level": "knowledge", "is_user_edited": True}
    meta = NodeMetadata(**data)
    assert meta.dikw_level == DIKWLevel.KNOWLEDGE
    assert meta.is_user_edited is True
