"""
Unit tests for the SummarizationAgent.
"""

from collections.abc import Generator
from typing import cast
from unittest.mock import MagicMock, patch

import pytest
from langchain_core.messages import AIMessage

from domain_models.config import ProcessingConfig
from matome.agents.summarizer import SummarizationAgent
from matome.exceptions import SummarizationError
from matome.utils.prompts import COD_TEMPLATE


@pytest.fixture
def config() -> ProcessingConfig:
    return ProcessingConfig()


@pytest.fixture
def mock_llm() -> Generator[MagicMock, None, None]:
    """Mock the ChatOpenAI instance."""
    with patch("matome.agents.summarizer.ChatOpenAI") as mock:
        yield mock


@pytest.fixture
def agent(mock_llm: MagicMock, config: ProcessingConfig) -> SummarizationAgent:
    """Create a SummarizationAgent instance with a mocked LLM."""
    # We mock the internal llm attribute to avoid real API calls during init if any
    agent = SummarizationAgent(config)
    agent.llm = MagicMock()
    return agent


def test_initialization(mock_llm: MagicMock) -> None:
    """Test that the agent is initialized with the correct configuration."""
    # Patch get_openrouter_api_key to return a key, so initialization proceeds
    with patch("matome.agents.summarizer.get_openrouter_api_key", return_value="sk-test-key"):
        config = ProcessingConfig(llm_temperature=0.5, max_retries=5)
        _ = SummarizationAgent(config)
        # Verify ChatOpenAI was called with correct base_url and config values
        mock_llm.assert_called_with(
            model="gpt-4o",
            api_key="sk-test-key",
            base_url="https://openrouter.ai/api/v1",
            temperature=0.5,
            max_retries=5,
        )


def test_summarize_happy_path(agent: SummarizationAgent, config: ProcessingConfig) -> None:
    """Test the summarize method with a valid response."""
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

    # Check if prompt matches the template structure
    expected_prompt_start = COD_TEMPLATE.format(context=context)
    assert prompt_content == expected_prompt_start


def test_summarize_empty_context(agent: SummarizationAgent, config: ProcessingConfig) -> None:
    """Test behavior with empty context."""
    result = agent.summarize("", config)
    assert result == ""
    llm_mock = cast(MagicMock, agent.llm)
    llm_mock.invoke.assert_not_called()


def test_mock_mode(config: ProcessingConfig) -> None:
    """Test that the agent returns a static string in mock mode."""
    # Patch where it is imported in summarizer.py
    with patch("matome.agents.summarizer.get_openrouter_api_key", return_value="mock"):
        agent = SummarizationAgent(config)
        result = agent.summarize("some context", config)
        assert result.startswith("Summary of")
        assert "some context" in result


def test_summarize_missing_key(config: ProcessingConfig) -> None:
    """Test that ValueError (or SummarizationError) is raised if API key is missing and not in mock mode."""
    # Default get_openrouter_api_key returns None
    with patch("matome.agents.summarizer.get_openrouter_api_key", return_value=None):
        agent = SummarizationAgent(config)
        # agent.llm should be None
        assert agent.llm is None

        with pytest.raises(SummarizationError, match="LLM not initialized"):
            agent.summarize("some context", config)


def test_summarize_list_response(agent: SummarizationAgent, config: ProcessingConfig) -> None:
    """Test handling of list content in LLM response."""
    llm_mock = cast(MagicMock, agent.llm)
    llm_mock.invoke.return_value = AIMessage(content=["Part 1", "Part 2"])

    result = agent.summarize("context", config)
    assert "Part 1" in result
    assert "Part 2" in result


def test_summarize_int_response(agent: SummarizationAgent, config: ProcessingConfig) -> None:
    """Test handling of unexpected content type (e.g. int)."""
    mock_msg = MagicMock()
    mock_msg.content = 123
    llm_mock = cast(MagicMock, agent.llm)
    llm_mock.invoke.return_value = mock_msg

    result = agent.summarize("context", config)
    assert result == "123"


def test_summarize_exception(agent: SummarizationAgent, config: ProcessingConfig) -> None:
    """Test that exceptions are wrapped in SummarizationError."""
    llm_mock = cast(MagicMock, agent.llm)
    llm_mock.invoke.side_effect = Exception("API Fail")

    with pytest.raises(SummarizationError, match="Summarization failed"):
        agent.summarize("context", config)


def test_summarize_long_input_dos_prevention(
    agent: SummarizationAgent, config: ProcessingConfig
) -> None:
    """Test behavior with input containing potential DoS vectors (extremely long words)."""
    # config.max_word_length default is 1000
    long_word = "a" * (config.max_word_length + 1)

    with pytest.raises(ValueError, match="potential DoS vector"):
        agent.summarize(long_word, config)


# We removed test_summarize_retry_behavior as mocking tenacity is complex
# and integration test covers error handling (test_pipeline_errors.py)


def test_summarize_with_strategy(agent: SummarizationAgent, config: ProcessingConfig) -> None:
    """Test that the agent uses the provided strategy to format the prompt."""
    strategy_mock = MagicMock()
    strategy_mock.format_prompt.return_value = "Formatted Prompt"

    llm_mock = cast(MagicMock, agent.llm)
    llm_mock.invoke.return_value = AIMessage(content="Summary")

    result = agent.summarize("context", config, strategy=strategy_mock)

    assert result == "Summary"
    strategy_mock.format_prompt.assert_called_once_with("context")

    # Verify LLM was called with formatted prompt
    args, _ = llm_mock.invoke.call_args
    messages = args[0]
    assert messages[0].content == "Formatted Prompt"
