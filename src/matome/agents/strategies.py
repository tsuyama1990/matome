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
        """Returns DIKW Level: WISDOM."""
        return DIKWLevel.WISDOM

    def format_prompt(self, text: str, context: dict[str, Any] | None = None) -> str:
        """
        Formats the prompt using the WISDOM template.
        Ignores context unless specifically extended.
        """
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
        """Returns DIKW Level: KNOWLEDGE."""
        return DIKWLevel.KNOWLEDGE

    def format_prompt(self, text: str, context: dict[str, Any] | None = None) -> str:
        """Formats the prompt using the KNOWLEDGE template."""
        return KNOWLEDGE_TEMPLATE.format(context=text)


class InformationStrategy(PromptStrategy):
    """
    Strategy for generating Information-level summaries.
    Focus: Actionable steps, checklists, detailed facts.
    """

    @property
    def dikw_level(self) -> DIKWLevel:
        """Returns DIKW Level: INFORMATION."""
        return DIKWLevel.INFORMATION

    def format_prompt(self, text: str, context: dict[str, Any] | None = None) -> str:
        """Formats the prompt using the INFORMATION template."""
        return INFORMATION_TEMPLATE.format(context=text)


class ChainOfDensityStrategy(PromptStrategy):
    """
    Default strategy using Chain of Density or simple summarization.
    Used for backward compatibility or when DIKW mode is off.
    """

    @property
    def dikw_level(self) -> DIKWLevel:
        """Returns default DIKW Level: DATA."""
        # Default level if not specified
        return DIKWLevel.DATA

    def format_prompt(self, text: str, context: dict[str, Any] | None = None) -> str:
        """Formats the prompt using the Chain of Density (COD) template."""
        from matome.utils.prompts import COD_TEMPLATE

        return COD_TEMPLATE.format(context=text)


class RefinementStrategy(PromptStrategy):
    """
    Strategy for interactive refinement of a node.
    Wraps another strategy or acts standalone, injecting user instructions.
    """

    def __init__(self, base_strategy: PromptStrategy | None = None) -> None:
        self.base_strategy = base_strategy or ChainOfDensityStrategy()

    @property
    def dikw_level(self) -> DIKWLevel:
        """Delegates DIKW level to the base strategy."""
        return self.base_strategy.dikw_level

    def format_prompt(self, text: str, context: dict[str, Any] | None = None) -> str:
        """
        Wraps the base strategy's prompt with refinement instructions.
        Expects 'instruction' key in context.
        """
        instruction = context.get("instruction", "") if context else ""
        if not instruction:
            # Fallback to base strategy if no instruction
            return self.base_strategy.format_prompt(text, context)

        base_prompt = self.base_strategy.format_prompt(text, context)
        return f"{base_prompt}\n\nUSER INSTRUCTION: {instruction}"


# Registry for easy lookup from configuration strings
# Explicit type hint for Mypy
STRATEGY_REGISTRY: dict[str, type[PromptStrategy]] = {
    DIKWLevel.WISDOM.value: WisdomStrategy,
    DIKWLevel.KNOWLEDGE.value: KnowledgeStrategy,
    DIKWLevel.INFORMATION.value: InformationStrategy,
    "default": ChainOfDensityStrategy,
    "refinement": RefinementStrategy,
}
