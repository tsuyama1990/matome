from domain_models.data_schema import DIKWLevel
from matome.agents.strategies import (
    InformationStrategy,
    KnowledgeStrategy,
    WisdomStrategy,
)


def test_wisdom_strategy_format_prompt() -> None:
    """Test WisdomStrategy prompt formatting."""
    strategy = WisdomStrategy()
    text = "This is a test text."
    prompt = strategy.format_prompt(text)

    assert "aphorism" in prompt.lower() or "short" in prompt.lower()
    assert text in prompt


def test_wisdom_strategy_parse_output() -> None:
    """Test WisdomStrategy output parsing."""
    strategy = WisdomStrategy()
    response = "Life is short."
    result = strategy.parse_output(response)

    assert result["summary"] == "Life is short."
    assert "metadata" in result
    assert result["metadata"]["dikw_level"] == DIKWLevel.WISDOM


def test_knowledge_strategy_format_prompt() -> None:
    """Test KnowledgeStrategy prompt formatting."""
    strategy = KnowledgeStrategy()
    text = "This is a test text."
    prompt = strategy.format_prompt(text)

    assert (
        "mental models" in prompt.lower()
        or "frameworks" in prompt.lower()
        or "why" in prompt.lower()
    )
    assert text in prompt


def test_knowledge_strategy_parse_output() -> None:
    """Test KnowledgeStrategy output parsing."""
    strategy = KnowledgeStrategy()
    response = "## Key Concepts\n- Concept A"
    result = strategy.parse_output(response)

    assert result["summary"] == response.strip()
    assert "metadata" in result
    assert result["metadata"]["dikw_level"] == DIKWLevel.KNOWLEDGE


def test_information_strategy_format_prompt() -> None:
    """Test InformationStrategy prompt formatting."""
    strategy = InformationStrategy()
    text = "This is a test text."
    prompt = strategy.format_prompt(text)

    assert "actionable" in prompt.lower() or "checklist" in prompt.lower()
    assert text in prompt


def test_information_strategy_parse_output() -> None:
    """Test InformationStrategy output parsing."""
    strategy = InformationStrategy()
    response = "- [ ] Task 1"
    result = strategy.parse_output(response)

    assert result["summary"] == response.strip()
    assert "metadata" in result
    assert result["metadata"]["dikw_level"] == DIKWLevel.INFORMATION
