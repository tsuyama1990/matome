import sys
from pathlib import Path

# Add src to sys.path to allow imports from domain_models
src_path = Path(__file__).parent.parent / "src"
if str(src_path) not in sys.path:
    sys.path.append(str(src_path))

import pytest  # noqa: E402

from domain_models.manifest import Document  # noqa: E402


@pytest.fixture
def sample_text() -> str:
    return "This is a test. This is another sentence."


@pytest.fixture
def sample_document(sample_text: str) -> Document:
    return Document(content=sample_text, metadata={"filename": "test.txt"})
