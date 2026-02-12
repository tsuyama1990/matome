from matome.agents.strategies import BaseSummaryStrategy
from matome.utils.prompts import COD_TEMPLATE


def test_base_strategy_format_prompt_string() -> None:
    strategy = BaseSummaryStrategy()
    text = "Hello World"
    expected = COD_TEMPLATE.format(context=text)
    assert strategy.format_prompt(text) == expected


def test_base_strategy_format_prompt_list() -> None:
    strategy = BaseSummaryStrategy()
    text_list = ["Hello", "World"]
    expected = COD_TEMPLATE.format(context="Hello\n\nWorld")
    assert strategy.format_prompt(text_list) == expected


def test_base_strategy_parse_output() -> None:
    strategy = BaseSummaryStrategy()
    response = "  This is a summary.  "
    expected = {"summary": "This is a summary."}
    assert strategy.parse_output(response) == expected
