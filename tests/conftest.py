import pytest

from domain_models.manifest import Document


@pytest.fixture
def sample_text() -> str:
    return "This is a test. This is another sentence."

@pytest.fixture
def sample_document(sample_text: str) -> Document:
    return Document(content=sample_text, metadata={"filename": "test.txt"})
