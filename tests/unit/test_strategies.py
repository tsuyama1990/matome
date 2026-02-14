
from domain_models.types import DIKWLevel
from matome.agents.strategies import (
    ChainOfDensityStrategy,
    InformationStrategy,
    KnowledgeStrategy,
    WisdomStrategy,
)


def test_wisdom_strategy_level() -> None:
    strategy = WisdomStrategy()
    assert strategy.dikw_level == DIKWLevel.WISDOM


def test_wisdom_strategy_prompt() -> None:
    strategy = WisdomStrategy()
    text = "Some complex text about life."
    prompt = strategy.format_prompt(text)
    # Since we use templates, we expect keywords
    assert "philosophy" in prompt.lower() or "wisdom" in prompt.lower()
    assert text in prompt


def test_knowledge_strategy_level() -> None:
    strategy = KnowledgeStrategy()
    assert strategy.dikw_level == DIKWLevel.KNOWLEDGE


def test_knowledge_strategy_prompt() -> None:
    strategy = KnowledgeStrategy()
    text = "Some technical details."
    prompt = strategy.format_prompt(text)
    assert "framework" in prompt.lower() or "knowledge" in prompt.lower()
    assert text in prompt


def test_information_strategy_level() -> None:
    strategy = InformationStrategy()
    assert strategy.dikw_level == DIKWLevel.INFORMATION


def test_information_strategy_prompt() -> None:
    strategy = InformationStrategy()
    text = "Step 1: Do this. Step 2: Do that."
    prompt = strategy.format_prompt(text)
    assert "actionable" in prompt.lower() or "checklist" in prompt.lower()
    assert text in prompt


def test_chain_of_density_strategy_level() -> None:
    strategy = ChainOfDensityStrategy()
    assert strategy.dikw_level == DIKWLevel.DATA


def test_chain_of_density_strategy_prompt() -> None:
    strategy = ChainOfDensityStrategy()
    text = "Some raw data."
    prompt = strategy.format_prompt(text)
    assert "chain of density" in prompt.lower() or "high-density" in prompt.lower()
    assert text in prompt

from unittest.mock import MagicMock
from matome.agents.strategies import RefinementStrategy

def test_refinement_strategy_appending() -> None:
    """Test that RefinementStrategy appends instruction to base prompt."""
    base_mock = MagicMock()
    base_mock.format_prompt.return_value = "Base Prompt."
    base_mock.dikw_level = DIKWLevel.WISDOM

    strategy = RefinementStrategy(base_strategy=base_mock)

    context = {"instruction": "Make it better."}
    prompt = strategy.format_prompt("Source Text", context)

    # Check that base strategy was called
    base_mock.format_prompt.assert_called_with("Source Text", context)

    # Check structure
    assert "Base Prompt." in prompt
    assert "USER INSTRUCTION: Make it better." in prompt
    assert prompt.endswith("USER INSTRUCTION: Make it better.") or "USER INSTRUCTION: Make it better." in prompt

def test_refinement_strategy_no_instruction() -> None:
    """Test RefinementStrategy without instruction (should fall back to base)."""
    base_mock = MagicMock()
    base_mock.format_prompt.return_value = "Base Prompt."

    strategy = RefinementStrategy(base_strategy=base_mock)

    prompt = strategy.format_prompt("Source Text", {})

    assert prompt == "Base Prompt."
