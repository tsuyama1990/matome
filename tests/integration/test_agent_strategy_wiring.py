import pytest
from unittest.mock import MagicMock
from matome.agents.summarizer import SummarizationAgent
from matome.agents.strategies import PromptStrategy
from domain_models.config import ProcessingConfig

class MockStrategy:
    def create_prompt(self, context_chunks: list[str], current_level: int) -> str:
        return "MOCKED PROMPT"

    def parse_output(self, llm_output: str) -> str:
        return f"PARSED: {llm_output}"

def test_agent_strategy_injection() -> None:
    config = ProcessingConfig()
    strategy = MockStrategy()

    # Inject Mock LLM
    mock_llm = MagicMock()
    mock_llm.invoke.return_value = MagicMock(content="LLM OUTPUT")

    # This will fail until `prompt_strategy` is added to __init__
    agent = SummarizationAgent(config=config, llm=mock_llm, prompt_strategy=strategy) # type: ignore[call-arg, arg-type]

    # Summarize single text -> agent usually treats it as list of chunks internally or as context
    summary = agent.summarize("test text")

    # Verify LLM was called with the prompt from strategy
    assert mock_llm.invoke.called
    args, _ = mock_llm.invoke.call_args
    messages = args[0]

    # The message content should be "MOCKED PROMPT" because MockStrategy returns that
    assert messages[0].content == "MOCKED PROMPT"

    # Verify the output was parsed by strategy
    assert summary == "PARSED: LLM OUTPUT"
