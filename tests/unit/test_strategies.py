from matome.agents.strategies import BaseSummaryStrategy, PromptStrategy


def test_base_summary_strategy_implements_protocol() -> None:
    strategy = BaseSummaryStrategy()
    assert isinstance(strategy, PromptStrategy)


def test_base_summary_strategy_generate_prompt() -> None:
    strategy = BaseSummaryStrategy()
    context = "test context"
    prompt = strategy.generate_prompt(context)
    assert "test context" in prompt
    assert "Output ONLY the final, densest summary." in prompt


def test_base_summary_strategy_parse_response() -> None:
    strategy = BaseSummaryStrategy()
    response = "  summary text  "
    parsed = strategy.parse_response(response)
    assert parsed == "summary text"
