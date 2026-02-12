
import pytest

# This import will fail until I implement it
try:
    from matome.agents.strategies import BaseSummaryStrategy
except ImportError:
    pytest.skip("BaseSummaryStrategy not implemented yet", allow_module_level=True)

from matome.utils.prompts import COD_TEMPLATE


def test_base_strategy_format_prompt() -> None:
    strategy = BaseSummaryStrategy()
    text = "Hello World"
    # The default strategy should use COD_TEMPLATE
    prompt = strategy.format_prompt(text)

    # Simple check if text is in prompt
    assert text in prompt
    # Check if template is used (might be hard if template changes, but let's assume it follows existing logic)
    expected = COD_TEMPLATE.format(context=text)
    assert prompt == expected

def test_base_strategy_parse_output_text() -> None:
    strategy = BaseSummaryStrategy()
    # If LLM returns plain text
    response = "This is a summary."
    result = strategy.parse_output(response)
    assert result == {"summary": "This is a summary."}
