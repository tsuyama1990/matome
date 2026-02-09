"""
Test to ensure SummarizationAgent complies with Summarizer protocol.
"""
from unittest.mock import patch

from matome.agents.summarizer import SummarizationAgent
from matome.interfaces import Summarizer


def test_summarization_agent_implements_summarizer() -> None:
    """Verify that SummarizationAgent implements the Summarizer protocol."""
    # We patch init to avoid API key check or network calls during instantiation
    with patch("matome.agents.summarizer.get_openrouter_api_key", return_value="mock"):
        agent = SummarizationAgent()
        assert isinstance(agent, Summarizer)
