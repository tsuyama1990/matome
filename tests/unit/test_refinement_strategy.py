from typing import Any
from unittest.mock import MagicMock

import pytest

from matome.agents.strategies import RefinementStrategy
from matome.interfaces import PromptStrategy


@pytest.fixture
def base_strategy() -> MagicMock:
    strategy = MagicMock(spec=PromptStrategy)
    strategy.format_prompt.return_value = "Base Prompt"
    strategy.parse_output.return_value = {"summary": "Base Summary"}
    return strategy


def test_refinement_strategy_init(base_strategy: MagicMock) -> None:
    strategy = RefinementStrategy(base_strategy)
    assert strategy.base_strategy == base_strategy


def test_refinement_format_prompt_with_instruction(base_strategy: MagicMock) -> None:
    strategy = RefinementStrategy(base_strategy)
    context = {"instruction": "Make it shorter"}
    prompt = strategy.format_prompt("text", context)

    # Assert base prompt is included
    assert "Base Prompt" in prompt
    # Assert instruction is included (via REFINEMENT_INSTRUCTION_TEMPLATE)
    assert "Make it shorter" in prompt
    assert "IMPORTANT - USER REFINEMENT INSTRUCTION" in prompt


def test_refinement_format_prompt_no_instruction(base_strategy: MagicMock) -> None:
    strategy = RefinementStrategy(base_strategy)
    context: dict[str, Any] = {}
    prompt = strategy.format_prompt("text", context)

    assert prompt == "Base Prompt"
    assert "IMPORTANT - USER REFINEMENT INSTRUCTION" not in prompt


def test_refinement_parse_output(base_strategy: MagicMock) -> None:
    strategy = RefinementStrategy(base_strategy)
    response = "Response"
    result = strategy.parse_output(response)

    base_strategy.parse_output.assert_called_with(response)
    assert result == {"summary": "Base Summary"}
