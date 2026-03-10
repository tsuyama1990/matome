import pytest
from pydantic import ValidationError

from src.domain_models.node import ContentNode, DocumentNode, IdentityNode


def test_identity_node_valid() -> None:
    node = IdentityNode()
    assert node.id is not None
    assert node.locked is True


def test_identity_node_invalid_extra() -> None:
    with pytest.raises(ValidationError):
        IdentityNode(unknown_field="test")  # type: ignore


def test_content_node_valid() -> None:
    node = ContentNode(raw_text="Hello world")
    assert node.raw_text == "Hello world"
    assert node.entities == []


def test_content_node_invalid_text_length() -> None:
    # Actually, min_length=0 is valid for empty strings, but let's test missing raw_text
    with pytest.raises(ValidationError):
        ContentNode()  # type: ignore


def test_content_node_invalid_extra() -> None:
    with pytest.raises(ValidationError):
        ContentNode(raw_text="Hi", extra_field=123)  # type: ignore


def test_document_node_valid() -> None:
    identity = IdentityNode()
    content = ContentNode(raw_text="Document contents here")
    doc = DocumentNode(identity=identity, content=content)
    assert doc.identity.id == identity.id
    assert doc.content.raw_text == content.raw_text


def test_document_node_invalid_extra() -> None:
    identity = IdentityNode()
    content = ContentNode(raw_text="Document contents here")
    with pytest.raises(ValidationError):
        DocumentNode(identity=identity, content=content, other="bad")  # type: ignore
