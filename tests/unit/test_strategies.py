from typing import Protocol, runtime_checkable

from matome.agents.strategies import BaseSummaryStrategy, PromptStrategy


def test_prompt_strategy_protocol() -> None:
    @runtime_checkable
    class MyStrategy(PromptStrategy, Protocol):
        pass

    # Runtime checkable protocol check
    # Note: BaseSummaryStrategy implements PromptStrategy, so subclass check might work if it inherits or is registered.
    # Protocol subclass check usually requires explicit inheritance or implementation matching.
    # We can check instantiation.
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
