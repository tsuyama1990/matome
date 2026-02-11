from matome.agents.strategies import (
    ActionStrategy,
    BaseSummaryStrategy,
    KnowledgeStrategy,
    PromptStrategy,
    RefinementStrategy,
    WisdomStrategy,
)
from matome.utils.prompts import (
    ACTION_TEMPLATE,
    COD_TEMPLATE,
    KNOWLEDGE_TEMPLATE,
    WISDOM_TEMPLATE,
)


def test_base_strategy_creation() -> None:
    """Test that BaseSummaryStrategy is created correctly."""
    strategy = BaseSummaryStrategy()
    assert isinstance(strategy, PromptStrategy)


def test_base_strategy_prompt_generation() -> None:
    """Test that BaseSummaryStrategy generates the expected prompt."""
    strategy = BaseSummaryStrategy()
    text = "Sample text for summarization."
    prompt = strategy.create_prompt(text)

    expected_prompt = COD_TEMPLATE.format(context=text)
    assert prompt == expected_prompt


def test_base_strategy_with_context() -> None:
    """Test that BaseSummaryStrategy ignores context (as it's simple COD for now)."""
    strategy = BaseSummaryStrategy()
    text = "Sample text."
    prompt = strategy.create_prompt(text, context={"level": 2})

    expected_prompt = COD_TEMPLATE.format(context=text)
    assert prompt == expected_prompt


def test_action_strategy() -> None:
    """Test ActionStrategy uses correct template."""
    strategy = ActionStrategy()
    text = "text"
    prompt = strategy.create_prompt(text)
    assert ACTION_TEMPLATE.format(context=text) == prompt


def test_knowledge_strategy() -> None:
    """Test KnowledgeStrategy uses correct template."""
    strategy = KnowledgeStrategy()
    text = "text"
    prompt = strategy.create_prompt(text)
    assert KNOWLEDGE_TEMPLATE.format(context=text) == prompt


def test_wisdom_strategy() -> None:
    """Test WisdomStrategy uses correct template."""
    strategy = WisdomStrategy()
    text = "text"
    prompt = strategy.create_prompt(text)
    assert WISDOM_TEMPLATE.format(context=text) == prompt


def test_refinement_strategy() -> None:
    """Test RefinementStrategy includes text and instructions."""
    strategy = RefinementStrategy("Make it shorter")
    text = "text"
    prompt = strategy.create_prompt(text)
    assert "Original Text:\ntext" in prompt
    assert "User Instructions:\nMake it shorter" in prompt


def test_strategies_handle_list() -> None:
    """Test strategies handle list of strings."""
    text = ["A", "B"]
    expected = "A\n\nB"

    s1 = ActionStrategy()
    assert expected in s1.create_prompt(text)

    s2 = RefinementStrategy("Inst")
    assert expected in s2.create_prompt(text)
