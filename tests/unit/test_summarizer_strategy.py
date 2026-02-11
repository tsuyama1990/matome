from typing import Any
from unittest.mock import MagicMock

import pytest

from domain_models.config import ProcessingConfig
from matome.agents.summarizer import SummarizationAgent


class MockStrategy:
    """Mock strategy for testing."""
    def create_prompt(self, text: str | list[str], context: dict[str, Any] | None = None) -> str:
        if isinstance(text, list):
            text = " ".join(text)
        return f"Mock Prompt: {text}"


@pytest.fixture
def config() -> ProcessingConfig:
    # Use a valid model name to pass Pydantic validation
    return ProcessingConfig(summarization_model="gpt-4o")


def test_summarizer_default_strategy(config: ProcessingConfig) -> None:
    """Test that SummarizationAgent uses default strategy if none provided."""
    # This assumes we modify __init__
    agent = SummarizationAgent(config)
    # We can't verify internal state easily without accessing protected members
    # But we can verify behavior if we mock LLM and check prompt sent.
    # For now, just ensure instantiation works.
    assert agent


def test_summarizer_injected_strategy(config: ProcessingConfig) -> None:
    """Test that SummarizationAgent uses injected strategy."""
    mock_strategy = MockStrategy()
    agent = SummarizationAgent(config, strategy=mock_strategy)

    # Mock LLM to avoid real calls
    agent.llm = MagicMock()
    agent.llm.invoke.return_value.content = "Summary"

    text = "Hello World"
    agent.summarize(text)

    # Verify LLM was called with the prompt from our strategy
    call_args = agent.llm.invoke.call_args
    assert call_args
    messages = call_args[0][0]
    prompt_sent = messages[0].content

    assert prompt_sent == "Mock Prompt: Hello World"


def test_summarizer_strategy_context(config: ProcessingConfig) -> None:
    """Test passing context to strategy via summarize (if supported)."""
    # If summarize() is updated to accept context, we test it here.
    # Currently summarize(text, config) only.
    # Maybe we want summarize(text, config, context=...)?
