from unittest.mock import MagicMock

import pytest
from langchain_core.messages import AIMessage, HumanMessage

from domain_models.config import ProcessingConfig
from matome.agents.strategies import WisdomStrategy
from matome.agents.summarizer import SummarizationAgent


@pytest.fixture
def mock_llm():
    llm = MagicMock()
    llm.invoke.return_value = AIMessage(content="Mock Summary")
    return llm


@pytest.fixture
def config():
    return ProcessingConfig()


def test_summarize_with_strategy(mock_llm, config):
    agent = SummarizationAgent(config, llm=mock_llm)
    strategy = WisdomStrategy()
    text = "Some context"

    # This call is expected to succeed once implementation is done
    # For TDD, it will fail now due to unexpected argument
    try:
        summary = agent.summarize(text, strategy=strategy)
    except TypeError:
        pytest.fail("SummarizationAgent.summarize() does not accept 'strategy' argument yet.")

    assert summary == "Mock Summary"

    # Verify LLM was called with the correct prompt
    expected_prompt = strategy.format_prompt(text)
    mock_llm.invoke.assert_called_once()
    args, _ = mock_llm.invoke.call_args
    messages = args[0]
    assert isinstance(messages[0], HumanMessage)
    assert messages[0].content == expected_prompt

def test_summarize_without_strategy_uses_default(mock_llm, config):
    agent = SummarizationAgent(config, llm=mock_llm)
    text = "Some context"

    summary = agent.summarize(text)
    assert summary == "Mock Summary"

    # Should use COD_TEMPLATE by default
    from matome.utils.prompts import COD_TEMPLATE
    expected_prompt = COD_TEMPLATE.format(context=text)
    mock_llm.invoke.assert_called_once()
    args, _ = mock_llm.invoke.call_args
    assert args[0][0].content == expected_prompt
