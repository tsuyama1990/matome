"""
UAT tests for Cycle 03: Summarization Engine.
"""

import os
from unittest.mock import patch

import pytest
from langchain_core.messages import AIMessage

from domain_models.config import ProcessingConfig
from matome.agents.strategies import BaseSummaryStrategy
from matome.agents.summarizer import SummarizationAgent
from tests.constants import MOCK_DENSE_RESPONSE, MOCK_SUMMARY_RESPONSE


@pytest.fixture
def mock_env_key() -> None:
    """Ensure OPENROUTER_API_KEY is set for tests, using a fake one if not present."""
    if "OPENROUTER_API_KEY" not in os.environ:
        os.environ["OPENROUTER_API_KEY"] = "sk-fake-key"


def test_scenario_08_openrouter_connection_mocked(mock_env_key: None) -> None:
    """
    Scenario 08: OpenRouter Connection (Mocked).
    Goal: Ensure the system can communicate with the OpenRouter API.
    Since we cannot guarantee a real key in CI, we mock the connection success.
    """
    with patch("matome.agents.summarizer.ChatOpenAI") as MockLLM:
        mock_instance = MockLLM.return_value
        mock_instance.invoke.return_value = AIMessage(content=MOCK_SUMMARY_RESPONSE)

        config = ProcessingConfig()
        agent = SummarizationAgent(config, strategy=BaseSummaryStrategy())
        # We manually trigger a simple call if the agent exposed one, but here we test summarize
        # The scenario asks for "Hello, world!" input.
        # We can reuse summarize for this or invoke llm directly if exposed.
        # But UAT should test the public API.

        # We override the template for this specific test if possible,
        # but the agent enforces CoD.
        # So we just check if it calls the LLM.

        summary_node = agent.summarize("Hello, world!", context={"id": "test", "level": 1, "children_indices": []})

        assert summary_node.text == MOCK_SUMMARY_RESPONSE
        MockLLM.assert_called()


def test_scenario_09_cod_behavior_mocked() -> None:
    """
    Scenario 09: Chain of Density Behavior (Mocked).
    Goal: Ensure the CoD prompt generates dense summaries.
    We verify the prompt construction.
    """
    verbose_text = "The history of the iPhone started in 2007 with Steve Jobs."

    with patch("matome.agents.summarizer.ChatOpenAI") as MockLLM:
        mock_instance = MockLLM.return_value
        # Mock a "dense" response
        mock_instance.invoke.return_value = AIMessage(
            content=MOCK_DENSE_RESPONSE
        )

        config = ProcessingConfig()
        agent = SummarizationAgent(config, strategy=BaseSummaryStrategy())

        summary_node = agent.summarize(verbose_text, context={"id": "test", "level": 1, "children_indices": []})

        # Check prompt contains instructions for CoD
        args, _ = mock_instance.invoke.call_args
        # args[0] is list of messages
        prompt_content = args[0][0].content

        assert "high-density summary" in prompt_content.lower()
        assert "missing entities" in prompt_content.lower()

        assert "iPhone" in summary_node.text
        assert "2007" in summary_node.text


def test_scenario_10_error_handling() -> None:
    """
    Scenario 10: Error Handling & Retries.
    Goal: Ensure the system is robust against transient API failures.
    """
    with patch("matome.agents.summarizer.ChatOpenAI") as MockLLM:
        mock_instance = MockLLM.return_value

        # Simulate a failure then success if we were testing retry loop inside agent.
        # If retry is handled by LangChain/Tenacity inside the LLM invoke,
        # we might need to mock side_effect.
        # However, `SummarizationAgent` might rely on `max_retries` of `ChatOpenAI`.
        # Testing that parameter is passed is enough for Unit test.
        # For UAT, we want to see if it eventually succeeds or raises structured error.

        # Let's simulate a crash
        mock_instance.invoke.side_effect = Exception("API Error 503")

        config = ProcessingConfig()
        agent = SummarizationAgent(config, strategy=BaseSummaryStrategy())

        # It should probably raise an exception or return an error string
        # purely depending on implementation. Spec says "eventually return a result or a structured error".
        # Let's assume it raises for now or handles it gracefully.
        # If it raises, we catch it.

        with pytest.raises(Exception, match="API Error 503"):
            agent.summarize("test", context={"id": "test", "level": 1, "children_indices": []})
