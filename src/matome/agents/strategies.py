from typing import Any

from matome.utils.prompts import COD_TEMPLATE


class BaseSummaryStrategy:
    """
    Implements the default summarization logic (Chain of Density).
    Preserves the behavior of Cycle 0.
    """

    def format_prompt(
        self, text: str | list[str], context: dict[str, Any] | None = None
    ) -> str:
        """
        Format the prompt using the Chain of Density template.

        Args:
            text: The text to summarize. Can be a string or list of strings.
            context: Optional context (unused in BaseSummaryStrategy).

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
