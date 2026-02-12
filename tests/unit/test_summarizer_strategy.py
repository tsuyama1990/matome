from unittest.mock import MagicMock, Mock

import pytest

from domain_models.config import ProcessingConfig
from matome.agents.summarizer import SummarizationAgent
from matome.interfaces import PromptStrategy


# Mock LLM and config
@pytest.fixture
def mock_config() -> ProcessingConfig:
    return ProcessingConfig(
        summarization_model="mock-model",
        verification_model="mock-model",
        embedding_model="mock-model",
        max_retries=1,
    )


@pytest.fixture
def mock_llm() -> MagicMock:
    mock = MagicMock()
    mock.invoke.return_value.content = '{"summary": "MOCK LLM RESULT"}'
    return mock


def test_summarizer_uses_strategy(mock_config: ProcessingConfig, mock_llm: MagicMock) -> None:
    # Create a mock strategy
    mock_strategy = Mock(spec=PromptStrategy)
    mock_strategy.format_prompt.return_value = "MOCK PROMPT"
    mock_strategy.parse_output.return_value = {"summary": "MOCK STRATEGY RESULT"}

    # Initialize agent with mock LLM to avoid real API call
    # Note: We need to bypass mock_mode logic if we want to test LLM invocation with strategy
    # Or implement mock strategy behavior.
    # If we pass an LLM, mock_mode is disabled in current implementation (unless key is 'mock'?)
    # Wait, existing code: if llm: self.llm = llm.
    # So providing LLM overrides mock mode unless key='mock' explicitly enables it?
    # Actually mock_mode = api_key == "mock".
    # If we don't set api_key to 'mock', mock_mode is false.
    # But we need api_key to init LLM if we don't provide one.
    # Here we provide one. So api_key doesn't matter much except for logging?
    # Actually, SummarizationAgent checks self.mock_mode inside summarize().
    # If mock_mode is True, it returns static summary.
    # We want to test STRATEGY usage, so we want to AVOID internal mock_mode short-circuit.
    # So we should ensure api_key != "mock".

    # But get_openrouter_api_key might return 'mock' if env var is set.
    # We should patch it or ensure it's not 'mock'.

    agent = SummarizationAgent(mock_config, llm=mock_llm)
    # Force mock_mode to False to test strategy logic which calls LLM
    agent.mock_mode = False

    # Call summarize with strategy
    # This argument 'strategy' doesn't exist yet in implementation
    try:
        summary = agent.summarize("test text", strategy=mock_strategy)
    except TypeError:
        pytest.fail("SummarizationAgent.summarize() does not accept 'strategy' argument yet.")

    # Verification
    # 1. Check if strategy.format_prompt was called with correct text
    mock_strategy.format_prompt.assert_called_once_with("test text")

    # 2. Check if LLM was invoked with the formatted prompt
    # The agent wraps prompt in HumanMessage
    args, _ = mock_llm.invoke.call_args
    messages = args[0]
    assert messages[0].content == "MOCK PROMPT"

    # 3. Check if strategy.parse_output was called with LLM response
    # The LLM mock returns '{"summary": "MOCK LLM RESULT"}'
    mock_strategy.parse_output.assert_called_once()
    call_args = mock_strategy.parse_output.call_args
    assert "MOCK LLM RESULT" in str(call_args)

    # 4. Check return value
    # The agent returns the result of parse_output["summary"]?
    # The interface says parse_output returns dict. Summarize returns str.
    # So the agent must extract "summary" key or similar from the dict returned by strategy.
    # BaseSummaryStrategy probably returns {"summary": "..."}.
    # We mocked it to return {"summary": "MOCK STRATEGY RESULT"}.
    # The agent should return "MOCK STRATEGY RESULT".
    assert summary == "MOCK STRATEGY RESULT"
