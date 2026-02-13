from typing import Any
from unittest.mock import MagicMock

from matome.agents.strategies import RefinementStrategy, WisdomStrategy
from matome.utils.prompts import REFINEMENT_INSTRUCTION_TEMPLATE, WISDOM_TEMPLATE


def test_refinement_strategy_format_prompt() -> None:
    base_strategy = WisdomStrategy()
    strategy = RefinementStrategy(base_strategy)

    text = "Some text"
    instruction = "Make it shorter"
    context = {"instruction": instruction}

    prompt = strategy.format_prompt(text, context)

    expected_base_prompt = WISDOM_TEMPLATE.format(context=text)
    expected_instruction = REFINEMENT_INSTRUCTION_TEMPLATE.format(instruction=instruction)

    assert expected_base_prompt in prompt
    assert expected_instruction in prompt
    assert prompt.endswith(expected_instruction)


def test_refinement_strategy_no_instruction() -> None:
    base_strategy = WisdomStrategy()
    strategy = RefinementStrategy(base_strategy)

    text = "Some text"
    context: dict[str, Any] = {}

    prompt = strategy.format_prompt(text, context)

    expected_base_prompt = WISDOM_TEMPLATE.format(context=text)

    assert prompt == expected_base_prompt

    # Basic check to ensure instruction template part is not present
    # REFINEMENT_INSTRUCTION_TEMPLATE likely starts with newlines, so we strip
    template_core = REFINEMENT_INSTRUCTION_TEMPLATE.strip()
    if template_core:
        assert template_core not in prompt


def test_refinement_strategy_parse_output() -> None:
    base_strategy = MagicMock()
    strategy = RefinementStrategy(base_strategy)

    response = "Output"
    strategy.parse_output(response)

    base_strategy.parse_output.assert_called_once_with(response)
