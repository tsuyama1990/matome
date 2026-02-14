from unittest.mock import MagicMock, patch

import pytest
from langchain_core.messages import AIMessage, HumanMessage

from domain_models.config import ProcessingConfig
from matome.agents.summarizer import SummarizationAgent
from matome.exceptions import SummarizationError


@pytest.fixture
def mock_llm() -> MagicMock:
    llm = MagicMock()
    # Mock invoke to return a valid message
    llm.invoke.return_value = AIMessage(content="Summary")
    return llm


@pytest.fixture
def agent(mock_llm: MagicMock) -> SummarizationAgent:
    config = ProcessingConfig()
    return SummarizationAgent(config, llm=mock_llm)


def test_initialization(mock_llm: MagicMock) -> None:
    """Test that the agent is initialized with the correct configuration."""
    # Patch get_openrouter_api_key to return a key, so initialization proceeds
    with patch("matome.agents.summarizer.get_openrouter_api_key", return_value="sk-test-key"):
        config = ProcessingConfig(llm_temperature=0.5, max_retries=5)
        # We need to mock ChatOpenAI construction to verify calls
        with patch("matome.agents.summarizer.ChatOpenAI") as mock_chat_cls:
            _ = SummarizationAgent(config)

            # Verify ChatOpenAI was called with correct base_url and config values
            # Need to match exact calls including defaults or provided params
            mock_chat_cls.assert_called_with(
                model=config.summarization_model, # Use configured model name
                api_key="sk-test-key",
                base_url="https://openrouter.ai/api/v1",
                temperature=0.5,
                max_retries=5,
            )


def test_summarize_success(agent: SummarizationAgent) -> None:
    """Test successful summarization."""
    result = agent.summarize("Test input")
    assert result == "Summary"
    agent.llm.invoke.assert_called_once()  # type: ignore


def test_summarize_empty_input(agent: SummarizationAgent) -> None:
    """Test handling of empty input."""
    result = agent.summarize("")
    assert result == ""
    agent.llm.invoke.assert_not_called()  # type: ignore


def test_summarize_retry_logic() -> None:
    """Test that retries are attempted on failure."""
    config = ProcessingConfig(max_retries=2)
    mock_llm = MagicMock()
    # Fail once, then succeed
    mock_llm.invoke.side_effect = [Exception("API Error"), AIMessage(content="Retry Success")]

    agent = SummarizationAgent(config, llm=mock_llm)

    result = agent.summarize("Test input")
    assert result == "Retry Success"
    assert mock_llm.invoke.call_count == 2


def test_summarize_max_retries_exceeded() -> None:
    """Test that SummarizationError is raised after retries exhausted."""
    config = ProcessingConfig(max_retries=2)
    mock_llm = MagicMock()
    mock_llm.invoke.side_effect = Exception("API Persistent Error")

    agent = SummarizationAgent(config, llm=mock_llm)

    with pytest.raises(SummarizationError):
        agent.summarize("Test input")

    # Initial + 2 retries = 3 calls
    assert mock_llm.invoke.call_count == 3


def test_mock_mode() -> None:
    """Test behavior when API key is 'mock'."""
    with patch("matome.agents.summarizer.get_openrouter_api_key", return_value="mock"):
        config = ProcessingConfig()
        agent = SummarizationAgent(config)

        assert agent.mock_mode is True
        assert agent.llm is None

        result = agent.summarize("Test content")
        assert "Summary of" in result
