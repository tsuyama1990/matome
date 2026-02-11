import pytest
from unittest.mock import MagicMock
from langchain_core.messages import BaseMessage
from domain_models.config import ProcessingConfig
from matome.agents.summarizer import SummarizationAgent
from matome.agents.strategies import WisdomStrategy

def test_agent_uses_strategy() -> None:
    config = ProcessingConfig()
    # Mock LLM
    mock_llm = MagicMock()
    # Mock invoke return value
    mock_response = MagicMock(spec=BaseMessage)
    mock_response.content = "Summary"
    mock_llm.invoke.return_value = mock_response

    # Also support __call__ for fallback
    mock_llm.return_value = mock_response

    agent = SummarizationAgent(config, llm=mock_llm)
    strategy = WisdomStrategy()
    text = "input text"

    # We expect summarize to accept strategy
    agent.summarize(text, strategy=strategy) # type: ignore[call-arg]

    # Verify LLM called with strategy's prompt
    assert mock_llm.invoke.called
    args, _ = mock_llm.invoke.call_args
    messages = args[0]
    prompt_sent = messages[0].content

    # WisdomStrategy should have put specific keywords in prompt
    # If WisdomStrategy is implemented correctly, this assertion holds.
    # Currently it will fail because WisdomStrategy is not implemented.
    assert "aphorism" in prompt_sent.lower() or "truth" in prompt_sent.lower()
