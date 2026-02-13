from typing import Any

from domain_models.data_schema import DIKWLevel
from matome.interfaces import PromptStrategy
from matome.utils.prompts import (
    COD_TEMPLATE,
    INFORMATION_TEMPLATE,
    KNOWLEDGE_TEMPLATE,
    REFINEMENT_INSTRUCTION_TEMPLATE,
    WISDOM_TEMPLATE,
)


class BaseSummaryStrategy:
    """
    Implements the default summarization logic (Chain of Density).
    Preserves the behavior of Cycle 0.
    """

    def format_prompt(self, text: str | list[str], context: dict[str, Any] | None = None) -> str:
        """
        Format the prompt using the Chain of Density template.

        Args:
            text: The text to summarize. Can be a string or list of strings.
            context: Optional context containing additional information (e.g., node metadata).
                     Structure: {'instruction': str, 'metadata': dict, ...}

        Returns:
            The formatted prompt string.
        """
        if isinstance(text, list):
            text = "\n\n".join(text)
        return COD_TEMPLATE.format(context=text)

    def parse_output(self, response: str) -> dict[str, Any]:
        """
        Parse the output from the LLM.

        For BaseSummaryStrategy, this simply treats the entire response as the summary.

        Args:
            response: The raw response string from the LLM.

        Returns:
            A dictionary containing the summary.
        """
        return {"summary": response.strip()}


class WisdomStrategy:
    """
    Strategy for generating Wisdom level summaries (L1).
    """

    def format_prompt(self, text: str | list[str], context: dict[str, Any] | None = None) -> str:
        """
        Format the prompt for Wisdom generation.
        """
        if isinstance(text, list):
            text = "\n\n".join(text)
        return WISDOM_TEMPLATE.format(context=text)

    def parse_output(self, response: str) -> dict[str, Any]:
        """
        Parse the output for Wisdom.
        """
        return {
            "summary": response.strip(),
            "metadata": {"dikw_level": DIKWLevel.WISDOM},
        }


class KnowledgeStrategy:
    """
    Strategy for generating Knowledge level summaries (L2).
    """

    def format_prompt(self, text: str | list[str], context: dict[str, Any] | None = None) -> str:
        """
        Format the prompt for Knowledge generation.
        """
        if isinstance(text, list):
            text = "\n\n".join(text)
        return KNOWLEDGE_TEMPLATE.format(context=text)

    def parse_output(self, response: str) -> dict[str, Any]:
        """
        Parse the output for Knowledge.
        """
        return {
            "summary": response.strip(),
            "metadata": {"dikw_level": DIKWLevel.KNOWLEDGE},
        }


class InformationStrategy:
    """
    Strategy for generating Information level summaries (L3).
    """

    def format_prompt(self, text: str | list[str], context: dict[str, Any] | None = None) -> str:
        """
        Format the prompt for Information generation.
        """
        if isinstance(text, list):
            text = "\n\n".join(text)
        return INFORMATION_TEMPLATE.format(context=text)

    def parse_output(self, response: str) -> dict[str, Any]:
        """
        Parse the output for Information.
        """
        return {
            "summary": response.strip(),
            "metadata": {"dikw_level": DIKWLevel.INFORMATION},
        }


class RefinementStrategy:
    """
    Decorator strategy for refining an existing summary based on user instructions.
    Wraps a base strategy (Wisdom, Knowledge, etc.) and appends the instruction to the prompt.
    """

    def __init__(self, base_strategy: PromptStrategy) -> None:
        self.base_strategy = base_strategy

    def format_prompt(self, text: str | list[str], context: dict[str, Any] | None = None) -> str:
        """
        Format the prompt by appending the user instruction to the base strategy's prompt.
        """
        base_prompt = self.base_strategy.format_prompt(text, context)
        instruction = context.get("instruction", "") if context else ""

        if instruction:
            return base_prompt + REFINEMENT_INSTRUCTION_TEMPLATE.format(instruction=instruction)
        return base_prompt

    def parse_output(self, response: str) -> dict[str, Any]:
        """
        Delegate response parsing to the base strategy.
        """
        return self.base_strategy.parse_output(response)
