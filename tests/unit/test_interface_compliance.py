"""
Test to ensure SummarizationAgent complies with Summarizer protocol.
"""

import inspect
from unittest.mock import patch

from domain_models.config import ProcessingConfig
from matome.agents.summarizer import SummarizationAgent
from matome.interfaces import Summarizer


def test_summarization_agent_implements_summarizer() -> None:
    """Verify that SummarizationAgent implements the Summarizer protocol."""
    # We patch init to avoid API key check or network calls during instantiation
    config = ProcessingConfig()
    with patch("matome.agents.summarizer.get_openrouter_api_key", return_value="mock"):
        agent = SummarizationAgent(config)
        assert isinstance(agent, Summarizer)

        # Check signature compliance manually since runtime checkable doesn't check types strictly
        sig = inspect.signature(agent.summarize)
        params = list(sig.parameters.values())

        # We expect: text, config, level, (optional strategy)
        # text should be first
        assert params[0].name == "text"
        # We can't easily check type hints at runtime without complex inspection,
        # but mypy handles that.
