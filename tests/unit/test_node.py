import pytest
from pydantic import ValidationError

from src.domain_models import ContentNode, IdentityNode


def test_identity_node_valid() -> None:
    node = IdentityNode(id="n1", level=0, tags={"type": "root"})
    assert node.id == "n1"
    assert node.level == 0
    assert node.tags == {"type": "root"}
    assert node.is_locked is True  # default


def test_identity_node_forbid_extra() -> None:
    with pytest.raises(ValidationError):
        # Should raise error because `invalid_field` is not allowed
        IdentityNode(id="n1", level=0, invalid_field="test")  # type: ignore


def test_content_node_valid() -> None:
    node = ContentNode(id="n1", original_text="This is a test chunk.")
    assert node.id == "n1"
    assert node.original_text == "This is a test chunk."
    assert node.summary_text is None
    assert node.entities == []


def test_content_node_forbid_extra() -> None:
    with pytest.raises(ValidationError):
        # Should raise error because `extra_field` is not allowed
        ContentNode(id="n1", original_text="test", extra_field="test")  # type: ignore
