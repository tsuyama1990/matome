from unittest.mock import MagicMock, patch

import pytest

from domain_models.config import ProcessingConfig
from matome.agents.summarizer import SummarizationAgent
from matome.engines.cluster import GMMClusterer
from matome.engines.embedder import EmbeddingService
from matome.engines.token_chunker import JapaneseTokenChunker
from matome.exceptions import SummarizationError


def test_chunking_error_handling() -> None:
    """Test that chunking errors are propagated or handled."""
    # If text is empty, chunker might return empty list or raise error depending on implementation
    # JapaneseTokenChunker raises ValueError for empty text in some paths, or returns empty list.
    chunker = JapaneseTokenChunker()
    config = ProcessingConfig()

    # Empty text -> empty list
    assert chunker.split_text("", config) == []

def test_embedding_error_handling() -> None:
    """Test error handling in embedding service."""
    config = ProcessingConfig()
    # Mock model
    with patch("matome.engines.embedder.SentenceTransformer") as mock_cls:
        mock_instance = mock_cls.return_value
        mock_instance.encode.side_effect = Exception("Model Error")

        embedder = EmbeddingService(config)

        # embed_strings is a generator. Exception should be raised when consumed.
        gen = embedder.embed_strings(["test"])
        with pytest.raises(Exception, match="Model Error"):
            list(gen)

def test_clustering_error_handling() -> None:
    """Test error handling in clustering engine."""
    config = ProcessingConfig()
    engine = GMMClusterer()

    # Invalid config (not gmm)
    # Using object.__setattr__ to bypass frozen Pydantic model for testing
    bad_config = config.model_copy(update={"clustering_algorithm": "kmeans"})

    with pytest.raises(ValueError, match="Unsupported clustering algorithm"):
        engine.cluster_nodes([[0.1]], bad_config)

def test_summarization_error_handling() -> None:
    """Test error handling in summarization agent."""
    config = ProcessingConfig()

    # Mock API key presence
    with patch("matome.agents.summarizer.get_openrouter_api_key", return_value="sk-key"):
        agent = SummarizationAgent(config)
        # Mock LLM failure
        agent.llm = MagicMock()
        agent.llm.invoke.side_effect = Exception("API Failure")

        with pytest.raises(SummarizationError, match="Summarization failed"):
            agent.summarize("text", config)
