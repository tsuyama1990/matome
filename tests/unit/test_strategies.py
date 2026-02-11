import pytest
from unittest.mock import MagicMock
from matome.agents.strategies import (
    BaseSummaryStrategy,
    WisdomStrategy,
    KnowledgeStrategy,
    InformationStrategy
)
from matome.utils.prompts import COD_TEMPLATE

def test_base_summary_strategy() -> None:
    strategy = BaseSummaryStrategy()
    text = "some text"
    prompt = strategy.format_prompt(text)
    assert text in prompt
    # Ideally check if it contains COD_TEMPLATE parts, but exact match might be brittle

def test_wisdom_strategy() -> None:
    strategy = WisdomStrategy()
    text = "some text"
    prompt = strategy.format_prompt(text)
    assert "aphorism" in prompt.lower() or "truth" in prompt.lower()
    assert "20-50 characters" in prompt or "concise" in prompt.lower()

def test_knowledge_strategy() -> None:
    strategy = KnowledgeStrategy()
    text = "some text"
    prompt = strategy.format_prompt(text)
    assert "mental models" in prompt.lower() or "frameworks" in prompt.lower()

def test_information_strategy() -> None:
    strategy = InformationStrategy()
    text = "some text"
    prompt = strategy.format_prompt(text)
    assert "action plan" in prompt.lower() or "checklist" in prompt.lower()
