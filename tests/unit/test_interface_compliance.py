

from matome.agents.strategies import BaseSummaryStrategy, PromptStrategy


def test_base_summary_strategy_compliance() -> None:
    strategy = BaseSummaryStrategy()

    # Check Protocol implementation
    assert isinstance(strategy, PromptStrategy)

    # Check method signatures
    assert hasattr(strategy, "create_prompt")
    assert hasattr(strategy, "parse_output")

    # Check execution
    context = ["chunk1"]
    prompt = strategy.create_prompt(context, current_level=1)
    assert isinstance(prompt, str)

    parsed = strategy.parse_output("output")
    assert isinstance(parsed, str)

    # Check Protocol structural typing explicitly with mypy (done via static analysis step)
    # Here we just check runtime behavior.
