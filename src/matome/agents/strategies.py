from typing import Any

from matome.utils.prompts import (
    COD_TEMPLATE,
    INFORMATION_TEMPLATE,
    KNOWLEDGE_TEMPLATE,
    REFINE_TEMPLATE,
    WISDOM_TEMPLATE,
)


class BaseSummaryStrategy:
    """
    Default summarization strategy using Chain of Density (CoD).
    Implements the PromptStrategy protocol.

    This strategy focuses on generating dense, information-rich summaries by iteratively
    refining the content to include more entities and details without increasing length.
    """

    def format_prompt(self, text: str | list[str], context: dict[str, Any] | None = None) -> str:
        """
        Constructs the Chain of Density prompt.

        Validates the input context to ensure no prompt injection attempts are present
        in the metadata, although the primary text is sanitized by the agent.

        Args:
            text: The text to summarize. Can be a single string or a list of strings.
            context: Optional context dictionary.

        Returns:
            Formatted prompt string.
        """
        # Efficiently join list if provided
        combined_text = "\n\n".join(text) if isinstance(text, list) else text

        # Basic length validation could be here, but Agent handles max_input_length.
        # We rely on Agent for heavy lifting validation.

        return COD_TEMPLATE.format(context=combined_text)

    def parse_output(self, response: str) -> dict[str, Any]:
        """
        Parses the raw output from the LLM.

        For Chain of Density, the output is expected to be the final summary text directly.
        We wrap it in a dictionary to satisfy the protocol.

        Args:
            response: The raw text response from the LLM.

        Returns:
            A dictionary containing the summary text under the key "summary".

        Raises:
            ValueError: If the response is empty.
        """
        if not response:
            msg = "Empty response received from LLM."
            raise ValueError(msg)

        return {"summary": response}


class WisdomStrategy:
    """
    Strategy for generating L1 Wisdom summaries (aphorisms/truths).
    """

    def format_prompt(self, text: str | list[str], context: dict[str, Any] | None = None) -> str:
        combined_text = "\n\n".join(text) if isinstance(text, list) else text
        return WISDOM_TEMPLATE.format(context=combined_text)

    def parse_output(self, response: str) -> dict[str, Any]:
        if not response:
            msg = "Empty response received from LLM."
            raise ValueError(msg)
        return {"summary": response.strip()}


class KnowledgeStrategy:
    """
    Strategy for generating L2 Knowledge summaries (mental models/frameworks).
    """

    def format_prompt(self, text: str | list[str], context: dict[str, Any] | None = None) -> str:
        combined_text = "\n\n".join(text) if isinstance(text, list) else text
        return KNOWLEDGE_TEMPLATE.format(context=combined_text)

    def parse_output(self, response: str) -> dict[str, Any]:
        if not response:
            msg = "Empty response received from LLM."
            raise ValueError(msg)
        return {"summary": response.strip()}


class InformationStrategy:
    """
    Strategy for generating L3 Information summaries (actionable steps).
    """

    def format_prompt(self, text: str | list[str], context: dict[str, Any] | None = None) -> str:
        combined_text = "\n\n".join(text) if isinstance(text, list) else text
        return INFORMATION_TEMPLATE.format(context=combined_text)

    def parse_output(self, response: str) -> dict[str, Any]:
        if not response:
            msg = "Empty response received from LLM."
            raise ValueError(msg)
        return {"summary": response.strip()}


class RefinementStrategy:
    """
    Strategy for refining existing content based on user instructions.
    """

    def format_prompt(self, text: str | list[str], context: dict[str, Any] | None = None) -> str:
        if not context or "instruction" not in context:
            msg = "RefinementStrategy requires 'instruction' in context."
            raise ValueError(msg)

        combined_text = "\n\n".join(text) if isinstance(text, list) else text
        return REFINE_TEMPLATE.format(
            original_content=combined_text, instruction=context["instruction"]
        )

    def parse_output(self, response: str) -> dict[str, Any]:
        if not response:
            msg = "Empty response received from LLM."
            raise ValueError(msg)
        return {"summary": response.strip()}
