from typing import Any

from matome.utils.prompts import COD_TEMPLATE


class BaseSummaryStrategy:
    """
    Default summarization strategy using Chain of Density (CoD).
    Implements the PromptStrategy protocol.
    """

    def format_prompt(self, text: str, context: dict[str, Any] | None = None) -> str:
        """
        Constructs the Chain of Density prompt.

        Args:
            text: The text to summarize.
            context: Optional context (ignored in base strategy).

        Returns:
            Formatted prompt string.
        """
        return COD_TEMPLATE.format(context=text)

    def parse_output(self, response: str) -> dict[str, Any]:
        """
        Parses the raw output from the LLM.

        For Chain of Density, the output is expected to be the final summary text directly.
        We wrap it in a dictionary to satisfy the protocol.

        Args:
            response: The raw text response from the LLM.

        Returns:
            A dictionary containing the summary text under the key "summary".
        """
        return {"summary": response}
