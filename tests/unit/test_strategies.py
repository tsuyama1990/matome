
# These imports will fail until I implement them
from matome.agents.strategies import BaseSummaryStrategy, PromptStrategy
from matome.utils.prompts import COD_TEMPLATE


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
