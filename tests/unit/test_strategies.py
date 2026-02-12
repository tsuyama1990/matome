import pytest

from matome.agents.strategies import (
    BaseSummaryStrategy,
    InformationStrategy,
    KnowledgeStrategy,
    RefinementStrategy,
    WisdomStrategy,
)
from matome.utils.prompts import (
    COD_TEMPLATE,
    INFORMATION_TEMPLATE,
    KNOWLEDGE_TEMPLATE,
    REFINE_TEMPLATE,
    WISDOM_TEMPLATE,
)


def test_base_summary_strategy() -> None:
    strategy = BaseSummaryStrategy()
    text = "Hello world"
    prompt = strategy.format_prompt(text)
    assert COD_TEMPLATE.format(context=text) in prompt
    assert strategy.parse_output("Summary") == {"summary": "Summary"}


def test_wisdom_strategy() -> None:
    strategy = WisdomStrategy()
    text = "Philosophical text"
    prompt = strategy.format_prompt(text)
    assert WISDOM_TEMPLATE.format(context=text) in prompt
    assert strategy.parse_output("Wisdom") == {"summary": "Wisdom"}


def test_knowledge_strategy() -> None:
    strategy = KnowledgeStrategy()
    text = "Scientific text"
    prompt = strategy.format_prompt(text)
    assert KNOWLEDGE_TEMPLATE.format(context=text) in prompt
    assert strategy.parse_output("Knowledge") == {"summary": "Knowledge"}


def test_information_strategy() -> None:
    strategy = InformationStrategy()
    text = "Instructional text"
    prompt = strategy.format_prompt(text)
    assert INFORMATION_TEMPLATE.format(context=text) in prompt
    assert strategy.parse_output("Information") == {"summary": "Information"}


def test_refinement_strategy() -> None:
    strategy = RefinementStrategy()
    text = "Original text"
    instruction = "Make it shorter"

    # Test missing context
    with pytest.raises(ValueError, match="requires 'instruction'"):
        strategy.format_prompt(text)

    # Test valid context
    context = {"instruction": instruction}
    prompt = strategy.format_prompt(text, context)
    expected = REFINE_TEMPLATE.format(original_content=text, instruction=instruction)
    assert expected in prompt

    assert strategy.parse_output("Refined text") == {"summary": "Refined text"}
