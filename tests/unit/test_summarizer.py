"""
Unit tests for the SummarizationAgent (Refactored for Strategy Pattern).
"""

from collections.abc import Generator
from typing import cast
from unittest.mock import MagicMock, patch

import pytest
from langchain_core.messages import AIMessage

from domain_models.config import ProcessingConfig
from domain_models.data_schema import DIKWLevel
from domain_models.manifest import SummaryNode
from matome.agents.summarizer import SummarizationAgent
from matome.exceptions import SummarizationError
from matome.interfaces import PromptStrategy


@pytest.fixture
def config() -> ProcessingConfig:
    return ProcessingConfig()


@pytest.fixture
def mock_strategy() -> MagicMock:
    strategy = MagicMock(spec=PromptStrategy)
    strategy.format_prompt.return_value = "Mock Prompt"
    strategy.parse_output.return_value = {"summary": "Mock Summary"}
    return strategy


@pytest.fixture
def mock_llm() -> Generator[MagicMock, None, None]:
    """Mock the ChatOpenAI instance."""
    with patch("matome.agents.summarizer.ChatOpenAI") as mock:
        yield mock


@pytest.fixture
def agent(
    mock_llm: MagicMock, config: ProcessingConfig, mock_strategy: MagicMock
) -> SummarizationAgent:
    """Create a SummarizationAgent instance with a mocked LLM and strategy."""
    agent = SummarizationAgent(config, strategy=mock_strategy)
    agent.llm = MagicMock()
    return agent


def test_initialization_with_strategy(
    mock_llm: MagicMock, mock_strategy: MagicMock
) -> None:
    """Test that the agent is initialized with the injected strategy."""
    with patch(
        "matome.agents.summarizer.get_openrouter_api_key", return_value="sk-test-key"
    ):
        config = ProcessingConfig()
        agent = SummarizationAgent(config, strategy=mock_strategy)
        assert agent.strategy == mock_strategy
        assert agent.llm is not None


def test_summarize_delegates_to_strategy(
    agent: SummarizationAgent, mock_strategy: MagicMock
) -> None:
    """Test that summarize calls strategy methods."""
    context = {"id": "123", "level": 1, "children_indices": [0]}
    text = "Input Text"

    llm_mock = cast(MagicMock, agent.llm)
    llm_mock.invoke.return_value = AIMessage(content="Raw Response")

    result = agent.summarize(text, context=context)

    # Assert format_prompt called
    mock_strategy.format_prompt.assert_called_with(text, context)

    # Assert LLM invoked with formatted prompt
    llm_mock.invoke.assert_called()
    args, _ = llm_mock.invoke.call_args
    assert args[0][0].content == "Mock Prompt"

    # Assert parse_output called
    mock_strategy.parse_output.assert_called_with("Raw Response")

    # Assert result is SummaryNode and fields are populated
    assert isinstance(result, SummaryNode)
    assert result.text == "Mock Summary"
    assert result.id == "123"


def test_summarize_merges_context(
    agent: SummarizationAgent, mock_strategy: MagicMock
) -> None:
    """Test that context fields are merged into SummaryNode."""
    context = {
        "id": "node-1",
        "level": 2,
        "children_indices": [10, 11],
        "metadata": {"cluster_id": 99},
    }
    mock_strategy.parse_output.return_value = {"summary": "Summary text"}

    llm_mock = cast(MagicMock, agent.llm)
    llm_mock.invoke.return_value = AIMessage(content="Raw")

    result = agent.summarize("text", context=context)

    assert result.id == "node-1"
    assert result.level == 2
    assert result.children_indices == [10, 11]
    # Update: Metadata is now an object, use attribute access
    assert result.metadata.cluster_id == 99
    # Also verify default level was added
    assert result.metadata.dikw_level == DIKWLevel.DATA
    assert result.text == "Summary text"


def test_summarize_renames_summary_key(
    agent: SummarizationAgent, mock_strategy: MagicMock
) -> None:
    """Test that 'summary' key from strategy is renamed to 'text' for SummaryNode."""
    context = {"id": "1", "level": 1, "children_indices": []}
    mock_strategy.parse_output.return_value = {"summary": "The summary"}

    llm_mock = cast(MagicMock, agent.llm)
    llm_mock.invoke.return_value = AIMessage(content="Raw")

    result = agent.summarize("text", context=context)
    assert result.text == "The summary"


def test_summarize_list_input(
    agent: SummarizationAgent, mock_strategy: MagicMock
) -> None:
    """Test that list input is passed to strategy."""
    context = {"id": "1", "level": 1, "children_indices": []}
    text_list = ["A", "B"]

    llm_mock = cast(MagicMock, agent.llm)
    llm_mock.invoke.return_value = AIMessage(content="Raw")

    agent.summarize(text_list, context=context)

    mock_strategy.format_prompt.assert_called_with(text_list, context)


def test_mock_mode_returns_node(
    config: ProcessingConfig, mock_strategy: MagicMock
) -> None:
    """Test that mock mode returns a valid SummaryNode."""
    with patch("matome.agents.summarizer.get_openrouter_api_key", return_value="mock"):
        agent = SummarizationAgent(config, strategy=mock_strategy)
        context = {"id": "mock-id", "level": 1, "children_indices": []}
        result = agent.summarize("some context", context=context)

        assert isinstance(result, SummaryNode)
        assert result.text.startswith("Summary of")
        assert result.id == "mock-id"
        assert result.metadata.dikw_level == DIKWLevel.DATA


def test_summarize_missing_key(
    config: ProcessingConfig, mock_strategy: MagicMock
) -> None:
    """Test that SummarizationError is raised if API key is missing."""
    with patch("matome.agents.summarizer.get_openrouter_api_key", return_value=None):
        agent = SummarizationAgent(config, strategy=mock_strategy)
        assert agent.llm is None

        with pytest.raises(SummarizationError, match="LLM not initialized"):
            agent.summarize(
                "some context", context={"id": "1", "level": 1, "children_indices": []}
            )


def test_summarize_long_input_dos_prevention(
    agent: SummarizationAgent, config: ProcessingConfig
) -> None:
    """Test behavior with input containing potential DoS vectors."""
    long_word = "a" * 1001
    context = {"id": "1", "level": 1, "children_indices": []}
    with pytest.raises(ValueError, match="potential DoS vector"):
        agent.summarize(long_word, context=context)
