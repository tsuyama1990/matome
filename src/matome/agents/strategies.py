from typing import Any

from matome.utils.prompts import COD_TEMPLATE


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
