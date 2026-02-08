"""
Unit tests for the SummarizationAgent.
"""
from typing import Generator, cast
from unittest.mock import MagicMock, patch

import pytest
from langchain_core.messages import AIMessage

from domain_models.config import ProcessingConfig
from matome.agents.summarizer import SummarizationAgent
from matome.utils.prompts import COD_TEMPLATE
from matome.exceptions import SummarizationError


@pytest.fixture
def mock_llm() -> Generator[MagicMock, None, None]:
    """Mock the ChatOpenAI instance."""
    with patch("matome.agents.summarizer.ChatOpenAI") as mock:
        yield mock


@pytest.fixture
def agent(mock_llm: MagicMock) -> SummarizationAgent:
    """Create a SummarizationAgent instance with a mocked LLM."""
    # We mock the internal llm attribute to avoid real API calls during init if any
    agent = SummarizationAgent()
    agent.llm = MagicMock()
    return agent


def test_initialization(mock_llm: MagicMock) -> None:
    """Test that the agent is initialized with the correct configuration."""
    # Patch get_openrouter_api_key to return a key, so initialization proceeds
    with patch("matome.agents.summarizer.get_openrouter_api_key", return_value="sk-test-key"):
        # Set config to have specific model
        _ = SummarizationAgent()
        # Verify ChatOpenAI was called with correct base_url
        mock_llm.assert_called_with(
            model="google/gemini-flash-1.5",
            api_key="sk-test-key",
            base_url="https://openrouter.ai/api/v1",
            temperature=0,
            max_retries=3,
        )


def test_summarize_happy_path(agent: SummarizationAgent) -> None:
    """Test the summarize method with a valid response."""
    config = ProcessingConfig()
    context = "This is a test context about AI."
    expected_summary = "AI is tested."

    # Mock the LLM response
    llm_mock = cast(MagicMock, agent.llm)
    llm_mock.invoke.return_value = AIMessage(content=expected_summary)

    result = agent.summarize(context, config)

    assert result == expected_summary
    # Verify the prompt contained the context and COD template
    args, _ = llm_mock.invoke.call_args
    # args[0] is the list of messages passed to invoke
    messages = args[0]
    assert len(messages) == 1
    prompt_content = messages[0].content

    # Check if prompt is formatted correctly (simplified check)
    assert context in prompt_content
    assert "High-Density Summary" in prompt_content or "high-density summary" in prompt_content


def test_summarize_empty_context(agent: SummarizationAgent) -> None:
    """Test behavior with empty context."""
    config = ProcessingConfig()
    result = agent.summarize("", config)
    assert result == ""
    llm_mock = cast(MagicMock, agent.llm)
    llm_mock.invoke.assert_not_called()


def test_mock_mode() -> None:
    """Test that the agent returns a static string in mock mode."""
    # Patch where it is imported in summarizer.py
    with patch("matome.agents.summarizer.get_openrouter_api_key", return_value="mock"):
        agent = SummarizationAgent()
        config = ProcessingConfig()
        result = agent.summarize("some context", config)
        assert result.startswith("Summary of")
        assert "some context" in result

def test_summarize_missing_key() -> None:
    """Test that ValueError (or SummarizationError) is raised if API key is missing and not in mock mode."""
    # Default get_openrouter_api_key returns None
    with patch("matome.agents.summarizer.get_openrouter_api_key", return_value=None):
        agent = SummarizationAgent()
        # agent.llm should be None
        assert agent.llm is None

        config = ProcessingConfig()
        with pytest.raises(SummarizationError, match="OpenRouter API Key is missing"):
            agent.summarize("some context", config)

def test_summarize_list_response(agent: SummarizationAgent) -> None:
    """Test handling of list content in LLM response."""
    config = ProcessingConfig()
    llm_mock = cast(MagicMock, agent.llm)
    llm_mock.invoke.return_value = AIMessage(content=["Part 1", "Part 2"])

    result = agent.summarize("context", config)
    assert "Part 1" in result
    assert "Part 2" in result

def test_summarize_int_response(agent: SummarizationAgent) -> None:
    """Test handling of unexpected content type (e.g. int)."""
    config = ProcessingConfig()
    mock_msg = MagicMock()
    mock_msg.content = 123
    llm_mock = cast(MagicMock, agent.llm)
    llm_mock.invoke.return_value = mock_msg

    result = agent.summarize("context", config)
    assert result == "123"

def test_summarize_exception(agent: SummarizationAgent) -> None:
    """Test that exceptions are wrapped in SummarizationError."""
    config = ProcessingConfig()
    llm_mock = cast(MagicMock, agent.llm)
    llm_mock.invoke.side_effect = Exception("API Fail")

    with pytest.raises(SummarizationError, match="Summarization failed"):
        agent.summarize("context", config)

def test_summarize_long_input(agent: SummarizationAgent) -> None:
    """Test behavior with extremely long input text."""
    config = ProcessingConfig()
    long_text = "word " * 10000  # Simulate 10k words
    expected_summary = "Long summary."

    llm_mock = cast(MagicMock, agent.llm)
    llm_mock.invoke.return_value = AIMessage(content=expected_summary)

    result = agent.summarize(long_text, config)
    assert result == expected_summary

    # Verify the prompt was constructed correctly despite length
    args, _ = llm_mock.invoke.call_args
    prompt_content = args[0][0].content
    assert len(prompt_content) > len(long_text)
