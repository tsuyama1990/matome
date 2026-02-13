"""
Test to ensure SummarizationAgent complies with Summarizer protocol.
"""

from unittest.mock import patch

from domain_models.config import ProcessingConfig
from matome.agents.strategies import (
    BaseSummaryStrategy,
    InformationStrategy,
    KnowledgeStrategy,
    RefinementStrategy,
    WisdomStrategy,
)
from matome.agents.summarizer import SummarizationAgent
from matome.interfaces import PromptStrategy, Summarizer


def test_strategies_implement_prompt_strategy() -> None:
    """Verify that all strategy classes implement the PromptStrategy protocol."""
    strategies = [
        BaseSummaryStrategy(),
        WisdomStrategy(),
        KnowledgeStrategy(),
        InformationStrategy(),
        # RefinementStrategy requires a base strategy
        RefinementStrategy(BaseSummaryStrategy()),
    ]

    for strategy in strategies:
        assert isinstance(strategy, PromptStrategy), (
            f"{type(strategy).__name__} does not implement PromptStrategy"
        )


def test_summarization_agent_implements_summarizer() -> None:
    """Verify that SummarizationAgent implements the Summarizer protocol."""
    # We patch init to avoid API key check or network calls during instantiation
    config = ProcessingConfig()
    with patch("matome.agents.summarizer.get_openrouter_api_key", return_value="mock"):
        agent = SummarizationAgent(config, strategy=BaseSummaryStrategy())
        assert isinstance(agent, Summarizer)
