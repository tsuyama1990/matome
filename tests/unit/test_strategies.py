from typing import Protocol, runtime_checkable

import pytest

from matome.agents.strategies import BaseSummaryStrategy, PromptStrategy


def test_prompt_strategy_protocol() -> None:
    @runtime_checkable
    class MyStrategy(PromptStrategy, Protocol):
        pass

    # Runtime checkable protocol check
    strategy = BaseSummaryStrategy()
    assert isinstance(strategy, PromptStrategy)


def test_base_summary_strategy() -> None:
    strategy = BaseSummaryStrategy()
    context = ["chunk1", "chunk2"]

    # We test with level=1 (arbitrary valid level)
    prompt = strategy.create_prompt(context, current_level=1)

    assert "chunk1" in prompt
    assert "chunk2" in prompt
    # Check for keywords from COD_TEMPLATE
    assert "high-density summary" in prompt.lower()

    output = "Here is the summary: This is the summary."
    parsed = strategy.parse_output(output)
    # Base strategy just returns the output as is (passthrough)
    assert parsed == output


def test_base_summary_strategy_empty_context() -> None:
    """Test behavior with empty context chunks."""
    strategy = BaseSummaryStrategy()
    context: list[str] = []

    # Empty context usually means COD template with empty context placeholder
    prompt = strategy.create_prompt(context, current_level=1)

    # Ensure it doesn't crash
    assert prompt is not None
    # COD_TEMPLATE has "{context}" placeholder. "".join([]) is empty string.
    # So "grouped by topic:\n{context}\n\nPlease generate" -> "grouped by topic:\n\n\nPlease generate"
    # Let's just check that it contains the text surrounding the context.
    assert "grouped by topic:" in prompt
    assert "Please generate a high-density summary" in prompt


def test_base_summary_strategy_invalid_level() -> None:
    """Test validation for invalid levels."""
    strategy = BaseSummaryStrategy()

    with pytest.raises(ValueError, match="Invalid level"):
        strategy.create_prompt(["text"], current_level=-1)
