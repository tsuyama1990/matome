from typing import Any

from domain_models.types import DIKWLevel
from matome.interfaces import PromptStrategy
from matome.utils.prompts import (
    INFORMATION_TEMPLATE,
    KNOWLEDGE_TEMPLATE,
    WISDOM_TEMPLATE,
)


class WisdomStrategy(PromptStrategy):
    """
    Strategy for generating Wisdom-level summaries.
    Focus: High-level philosophy, core insight, abstraction.
    """

    @property
    def dikw_level(self) -> DIKWLevel:
        return DIKWLevel.WISDOM

    def format_prompt(self, text: str, context: dict[str, Any] | None = None) -> str:
        # We might inject context/instructions if needed
        # But for now, we just use the template.
        return WISDOM_TEMPLATE.format(context=text)


class KnowledgeStrategy(PromptStrategy):
    """
    Strategy for generating Knowledge-level summaries.
    Focus: Frameworks, mechanisms, structured understanding.
    """

    @property
    def dikw_level(self) -> DIKWLevel:
        return DIKWLevel.KNOWLEDGE

    def format_prompt(self, text: str, context: dict[str, Any] | None = None) -> str:
        return KNOWLEDGE_TEMPLATE.format(context=text)


class InformationStrategy(PromptStrategy):
    """
    Strategy for generating Information-level summaries.
    Focus: Actionable steps, checklists, detailed facts.
    """

    @property
    def dikw_level(self) -> DIKWLevel:
        return DIKWLevel.INFORMATION

    def format_prompt(self, text: str, context: dict[str, Any] | None = None) -> str:
        return INFORMATION_TEMPLATE.format(context=text)


class BaseSummaryStrategy(PromptStrategy):
    """
    Default strategy using Chain of Density or simple summarization.
    Used for backward compatibility or when DIKW mode is off.
    """

    @property
    def dikw_level(self) -> DIKWLevel:
        # Default level if not specified
        return DIKWLevel.DATA

    def format_prompt(self, text: str, context: dict[str, Any] | None = None) -> str:
        from matome.utils.prompts import COD_TEMPLATE

        return COD_TEMPLATE.format(context=text)
