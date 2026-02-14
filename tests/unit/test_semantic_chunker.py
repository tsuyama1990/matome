import pytest
from unittest.mock import MagicMock
from domain_models.config import ProcessingConfig
from matome.engines.semantic_chunker import SemanticChunker

@pytest.fixture
def mock_embedder() -> MagicMock:
    return MagicMock()

@pytest.fixture
def config() -> ProcessingConfig:
    return ProcessingConfig()

def test_chunker_initialization(config: ProcessingConfig) -> None:
    chunker = SemanticChunker(config)
    assert chunker.model is not None

def test_split_text_stream(config: ProcessingConfig) -> None:
    # Mock model
    chunker = SemanticChunker(config)
    chunker.model = MagicMock()
    chunker.model.encode.return_value = [[0.1, 0.2], [0.2, 0.3], [0.8, 0.9]] # Mock embeddings

    # Mock input stream
    text = "Sentence one. Sentence two. Sentence three."

    # Run
    chunks = list(chunker.split_text(text, config))

    assert len(chunks) > 0
    assert chunks[0].index == 0
