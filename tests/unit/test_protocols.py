import pytest

from src.domain_models.node import DocumentNode
from src.domain_models.protocols import DocumentRepository


def test_abstract_protocol_cannot_be_instantiated() -> None:
    # Attempting to instantiate the base class directly should raise TypeError
    with pytest.raises(TypeError):
        DocumentRepository()  # type: ignore[abstract]


def test_incomplete_mock_protocol_raises_error() -> None:
    # Missing required abstract methods like save()
    class IncompleteDocumentRepository(DocumentRepository):
        def get_by_id(self, node_id: str) -> DocumentNode | None:
            return None

    with pytest.raises(TypeError):
        IncompleteDocumentRepository()  # type: ignore[abstract]
