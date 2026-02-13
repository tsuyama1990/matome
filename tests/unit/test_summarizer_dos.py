from unittest.mock import MagicMock, patch

import pytest
from langchain_core.messages import AIMessage

from domain_models.config import ProcessingConfig
from matome.agents.strategies import BaseSummaryStrategy
from matome.agents.summarizer import SummarizationAgent


@pytest.fixture
def config() -> ProcessingConfig:
    return ProcessingConfig()


@pytest.fixture
def agent(config: ProcessingConfig) -> SummarizationAgent:
    with patch("matome.agents.summarizer.get_openrouter_api_key", return_value="test_key"):
        agent = SummarizationAgent(config, strategy=BaseSummaryStrategy())
        agent.llm = MagicMock()
        return agent


def test_summarize_long_document_dos(agent: SummarizationAgent, config: ProcessingConfig) -> None:
    """
    Test protection against document length DoS.
    Max length is 500,000 characters.
    """
    # Just under limit
    # Should check max word length too, so we need spaces
    # 5000 chars per word max allowed (default 1000 now)
    # We construct safe text with spaces
    safe_text_words = ("a" * 100 + " ") * 4900  # ~495k chars

    # Mock LLM
    agent.llm.invoke.return_value = AIMessage(content="Summary")  # type: ignore

    # Safe text should pass validation
    result = agent.summarize(
        safe_text_words, context={"id": "test", "level": 1, "children_indices": []}
    )
    assert result.text == "Summary"

    # Over limit
    unsafe_text = "a" * 500_001
    with pytest.raises(ValueError, match="Input text exceeds maximum allowed length"):
        agent.summarize(unsafe_text, context={"id": "test", "level": 1, "children_indices": []})


def test_summarize_token_dos(agent: SummarizationAgent, config: ProcessingConfig) -> None:
    """Test protection against long words (tokenization bomb)."""
    # Config default max_word_length is 1000
    long_word = "a" * 1001
    with pytest.raises(ValueError, match="potential DoS vector"):
        agent.summarize(long_word, context={"id": "test", "level": 1, "children_indices": []})


def test_summarize_token_dos_multiple_long_words(
    agent: SummarizationAgent, config: ProcessingConfig
) -> None:
    """Test protection against multiple long words."""
    long_words = ("a" * 1001 + " ") * 3
    with pytest.raises(ValueError, match="potential DoS vector"):
        agent.summarize(long_words, context={"id": "test", "level": 1, "children_indices": []})
