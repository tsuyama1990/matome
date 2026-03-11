import pytest
from pydantic import ValidationError

from src.domain_models.node import ContentNode, DocumentNode, IdentityNode


def test_identity_node_valid() -> None:
    node = IdentityNode(id="uuid-1234", parent_id="root", tags={"axis": "system"})
    assert node.id == "uuid-1234"
    assert node.parent_id == "root"
    assert node.tags == {"axis": "system"}


def test_identity_node_extra_forbid() -> None:
    with pytest.raises(ValidationError):
        IdentityNode(id="123", extra="invalid")  # type: ignore[call-arg]


def test_content_node_valid() -> None:
    node = ContentNode(text="This is content", summary="Summary", entities=["EntityA"])
    assert node.text == "This is content"
    assert node.summary == "Summary"
    assert "EntityA" in node.entities


def test_content_node_extra_forbid() -> None:
    with pytest.raises(ValidationError):
        ContentNode(text="Test", invalid_field=123)  # type: ignore[call-arg]


def test_document_node_valid() -> None:
    identity = IdentityNode(id="doc-1")
    content = ContentNode(text="Doc text")
    doc = DocumentNode(identity=identity, content=content)

    assert doc.identity.id == "doc-1"
    assert doc.content.text == "Doc text"


def test_document_node_extra_forbid() -> None:
    with pytest.raises(ValidationError):
        DocumentNode(  # type: ignore[call-arg]
            identity=IdentityNode(id="1"),
            content=ContentNode(text="txt"),
            unwanted="field"
        )
