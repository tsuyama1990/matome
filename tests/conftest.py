import sys
import os

# Add src to python path so that domain_models can be imported
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(__file__)), "src"))

import pytest

from domain_models.manifest import Document


@pytest.fixture
def sample_text() -> str:
    return "This is a test. This is another sentence."

@pytest.fixture
def sample_document(sample_text: str) -> Document:
    return Document(content=sample_text, metadata={"filename": "test.txt"})
