from unittest.mock import MagicMock, patch

from langchain_core.messages import AIMessage

from domain_models.config import ProcessingConfig
from matome.agents.strategies import PromptStrategy
from matome.agents.summarizer import SummarizationAgent


class MockStrategy(PromptStrategy):
    """Mock strategy for wiring test."""

    def create_prompt(self, context_chunks: list[str], current_level: int) -> str:
        return f"WIRING CHECK: {current_level}"

    def parse_output(self, llm_output: str) -> str:
        return f"PARSED: {llm_output}"


def test_agent_strategy_wiring() -> None:
    """Verify that SummarizationAgent correctly delegates to the injected strategy."""
    config = ProcessingConfig()
    strategy = MockStrategy()

    with patch("matome.agents.summarizer.get_openrouter_api_key", return_value="mock"):
        agent = SummarizationAgent(config, prompt_strategy=strategy)
        agent.mock_mode = False
        agent.llm = MagicMock()
        llm_mock = agent.llm
        llm_mock.invoke.return_value = AIMessage(content="LLM_OUT")

        result = agent.summarize("context", config, level=42)

        # Verify prompt
        args, _ = llm_mock.invoke.call_args
        prompt = args[0][0].content
        assert prompt == "WIRING CHECK: 42"

        # Verify result
        assert result == "PARSED: LLM_OUT"
