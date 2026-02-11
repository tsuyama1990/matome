from matome.agents.strategies import BaseSummaryStrategy
from matome.utils.prompts import COD_TEMPLATE


def test_base_strategy_create_prompt() -> None:
    """Test that BaseSummaryStrategy creates prompt correctly."""
    strategy = BaseSummaryStrategy()
    chunks = ["Chunk 1", "Chunk 2"]
    # The implementation joins with "\n\n"
    expected_context = "Chunk 1\n\nChunk 2"
    expected_prompt = COD_TEMPLATE.format(context=expected_context)

    prompt = strategy.create_prompt(chunks, current_level=1)
    assert prompt == expected_prompt


def test_base_strategy_parse_output() -> None:
    """Test that BaseSummaryStrategy passes output through."""
    strategy = BaseSummaryStrategy()
    output = "Summary text"
    assert strategy.parse_output(output) == output
