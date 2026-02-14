from typing import Any

from domain_models.types import DIKWLevel
from matome.interfaces import PromptStrategy
from matome.utils.prompts import (
    INFORMATION_TEMPLATE,
    KNOWLEDGE_TEMPLATE,
    REFINEMENT_INSTRUCTION_TEMPLATE,
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


class RefinementStrategy(PromptStrategy):
    """
    Strategy for interactive refinement of a node.
    Wraps another strategy or acts standalone, injecting user instructions.
    """

    def __init__(self, base_strategy: PromptStrategy | None = None) -> None:
        self.base_strategy = base_strategy or BaseSummaryStrategy()

    @property
    def dikw_level(self) -> DIKWLevel:
        return self.base_strategy.dikw_level

    def format_prompt(self, text: str, context: dict[str, Any] | None = None) -> str:
        instruction = context.get("instruction", "") if context else ""
        if not instruction:
            # Fallback to base strategy if no instruction
            return self.base_strategy.format_prompt(text, context)

        return REFINEMENT_INSTRUCTION_TEMPLATE.format(context=text, instruction=instruction)


# Registry for easy lookup from configuration strings
STRATEGY_REGISTRY: dict[str, type[PromptStrategy]] = {
    DIKWLevel.WISDOM.value: WisdomStrategy,
    DIKWLevel.KNOWLEDGE.value: KnowledgeStrategy,
    DIKWLevel.INFORMATION.value: InformationStrategy,
    "default": BaseSummaryStrategy,
    "refinement": RefinementStrategy,
}
