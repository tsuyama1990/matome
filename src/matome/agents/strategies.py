from typing import Any

from matome.interfaces import PromptStrategy  # noqa: F401
from matome.utils.prompts import (
    ACTION_TEMPLATE,
    COD_TEMPLATE,
    KNOWLEDGE_TEMPLATE,
    WISDOM_TEMPLATE,
)


class BaseSummaryStrategy:
    """
    Default summarization strategy using Chain of Density (CoD).
    """

    def create_prompt(self, text: str | list[str], context: dict[str, Any] | None = None) -> str:
        """
        Generates the prompt using the standard Chain of Density template.

        Args:
            text: The input text to summarize.
            context: Optional context (ignored in base strategy).

        Returns:
            The formatted prompt string.
        """
        if isinstance(text, list):
            text = "\n\n".join(text)
        return COD_TEMPLATE.format(context=text)


class ActionStrategy:
    """
    Strategy for generating Actionable Information (Level 3 / Data Summaries).
    Focuses on "How-to", steps, and executable checklists.
    """

    def create_prompt(self, text: str | list[str], context: dict[str, Any] | None = None) -> str:
        """
        Generates the prompt for extracting actionable information.
        """
        if isinstance(text, list):
            text = "\n\n".join(text)
        return ACTION_TEMPLATE.format(context=text)


class KnowledgeStrategy:
    """
    Strategy for generating Knowledge Frameworks (Level 2 / Information Summaries).
    Focuses on "Why", mechanisms, and structural logic.
    """

    def create_prompt(self, text: str | list[str], context: dict[str, Any] | None = None) -> str:
        """
        Generates the prompt for synthesizing knowledge frameworks.
        """
        if isinstance(text, list):
            text = "\n\n".join(text)
        return KNOWLEDGE_TEMPLATE.format(context=text)


class WisdomStrategy:
    """
    Strategy for generating Wisdom/Principles (Level 1 / Knowledge Summaries).
    Focuses on concise aphorisms, core truths, and philosophy.
    """

    def create_prompt(self, text: str | list[str], context: dict[str, Any] | None = None) -> str:
        """
        Generates the prompt for distilling wisdom.
        """
        if isinstance(text, list):
            text = "\n\n".join(text)
        return WISDOM_TEMPLATE.format(context=text)


class RefinementStrategy:
    """
    Strategy for refining existing text based on user instructions.
    """

    def __init__(self, instructions: str) -> None:
        self.instructions = instructions

    def create_prompt(self, text: str | list[str], context: dict[str, Any] | None = None) -> str:
        """
        Generates the prompt for refinement.
        """
        if isinstance(text, list):
            text = "\n\n".join(text)
        # We ignore context instructions if any, and use self.instructions
        return (
            f"Original Text:\n{text}\n\n"
            f"User Instructions:\n{self.instructions}\n\n"
            "Please rewrite the text following the instructions strictly."
        )
