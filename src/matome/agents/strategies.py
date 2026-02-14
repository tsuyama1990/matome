from abc import ABC, abstractmethod

from domain_models.types import DIKWLevel
from matome.utils.prompts import (
    COD_TEMPLATE,
    INFORMATION_TEMPLATE,
    KNOWLEDGE_TEMPLATE,
    WISDOM_TEMPLATE,
)


class PromptStrategy(ABC):
    """Abstract base class for prompt strategies."""

    @abstractmethod
    def format_prompt(self, context: str) -> str:
        """Constructs the prompt for the LLM."""

    @property
    @abstractmethod
    def dikw_level(self) -> DIKWLevel:
        """Returns the target DIKW level."""


class WisdomStrategy(PromptStrategy):
    """Strategy for generating Wisdom nodes (Root)."""

    def format_prompt(self, context: str) -> str:
        return WISDOM_TEMPLATE.format(context=context)

    @property
    def dikw_level(self) -> DIKWLevel:
        return DIKWLevel.WISDOM


class KnowledgeStrategy(PromptStrategy):
    """Strategy for generating Knowledge nodes (Intermediate)."""

    def format_prompt(self, context: str) -> str:
        return KNOWLEDGE_TEMPLATE.format(context=context)

    @property
    def dikw_level(self) -> DIKWLevel:
        return DIKWLevel.KNOWLEDGE


class InformationStrategy(PromptStrategy):
    """Strategy for generating Information nodes (Leaf Summaries)."""

    def format_prompt(self, context: str) -> str:
        return INFORMATION_TEMPLATE.format(context=context)

    @property
    def dikw_level(self) -> DIKWLevel:
        return DIKWLevel.INFORMATION


class BaseSummaryStrategy(PromptStrategy):
    """Legacy strategy using Chain of Density (Default)."""

    def format_prompt(self, context: str) -> str:
        return COD_TEMPLATE.format(context=context)

    @property
    def dikw_level(self) -> DIKWLevel:
        return DIKWLevel.INFORMATION
