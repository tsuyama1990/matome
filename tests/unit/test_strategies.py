from domain_models.types import DIKWLevel
from matome.agents.strategies import (
    BaseSummaryStrategy,
    InformationStrategy,
    KnowledgeStrategy,
    WisdomStrategy,
)
from matome.utils.prompts import (
    COD_TEMPLATE,
    INFORMATION_TEMPLATE,
    KNOWLEDGE_TEMPLATE,
    WISDOM_TEMPLATE,
)


def test_wisdom_strategy():
    strategy = WisdomStrategy()
    assert strategy.dikw_level == DIKWLevel.WISDOM
    prompt = strategy.format_prompt("context")
    assert WISDOM_TEMPLATE.format(context="context") == prompt


def test_knowledge_strategy():
    strategy = KnowledgeStrategy()
    assert strategy.dikw_level == DIKWLevel.KNOWLEDGE
    prompt = strategy.format_prompt("context")
    assert KNOWLEDGE_TEMPLATE.format(context="context") == prompt


def test_information_strategy():
    strategy = InformationStrategy()
    assert strategy.dikw_level == DIKWLevel.INFORMATION
    prompt = strategy.format_prompt("context")
    assert INFORMATION_TEMPLATE.format(context="context") == prompt


def test_base_summary_strategy():
    strategy = BaseSummaryStrategy()
    # Default is INFORMATION as per implementation
    assert strategy.dikw_level == DIKWLevel.INFORMATION
    prompt = strategy.format_prompt("context")
    assert COD_TEMPLATE.format(context="context") == prompt
