"""
Agents package for Matome system.
Contains implementation of various agents like SummarizationAgent.
"""

from matome.agents.strategies import (
    BaseSummaryStrategy,
    InformationStrategy,
    KnowledgeStrategy,
    PromptStrategy,
    WisdomStrategy,
)
from matome.agents.summarizer import SummarizationAgent
from matome.agents.verifier import VerifierAgent

__all__ = [
    "BaseSummaryStrategy",
    "InformationStrategy",
    "KnowledgeStrategy",
    "PromptStrategy",
    "SummarizationAgent",
    "VerifierAgent",
    "WisdomStrategy",
]
