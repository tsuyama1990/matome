
from domain_models.types import DIKWLevel
from matome.agents.strategies import InformationStrategy, KnowledgeStrategy, WisdomStrategy


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
