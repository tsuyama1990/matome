from typing import Any, Protocol, runtime_checkable

from matome.utils.prompts import COD_TEMPLATE


@runtime_checkable
class PromptStrategy(Protocol):
    """
    Interface for generating prompts for the LLM.
    """

    def create_prompt(self, text: str, context: dict[str, Any] | None = None) -> str:
        """
        Generates the prompt string to be sent to the LLM.

        Args:
            text: The input text chunk(s) to summarize.
            context: Optional context (e.g., existing summary, tree level).

        Returns:
            The formatted prompt string.
        """
        ...


class BaseSummaryStrategy:
    """
    Default summarization strategy using Chain of Density (CoD).
    """

    def create_prompt(self, text: str, context: dict[str, Any] | None = None) -> str:
        """
        Generates the prompt using the standard Chain of Density template.

        Args:
            text: The input text to summarize.
            context: Optional context (ignored in base strategy).

        Returns:
            The formatted prompt string.
        """
        return COD_TEMPLATE.format(context=text)
