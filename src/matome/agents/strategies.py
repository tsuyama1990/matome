from typing import Protocol, runtime_checkable

from matome.utils.prompts import COD_TEMPLATE


@runtime_checkable
class PromptStrategy(Protocol):
    """
    Defines the contract for generating prompts and parsing responses
    for a specific DIKW level.
    """

    def create_prompt(self, context_chunks: list[str], current_level: int) -> str:
        """
        Constructs the LLM prompt based on the context and tree level.
        """
        ...

    def parse_output(self, llm_output: str) -> str:
        """
        Parses the raw LLM output into the final summary string.
        Useful for stripping "Here is the summary:" prefixes.
        """
        ...


class BaseSummaryStrategy:
    """
    Default implementation that mimics the existing Chain of Density logic.
    Used for backward compatibility and basic summarization.

    This strategy ignores the `current_level` parameter and treats all summarization
    requests uniformly using the standard COD template.
    """

    def create_prompt(self, context_chunks: list[str], current_level: int) -> str:
        """
        Constructs the LLM prompt based on the context and tree level.

        Uses the existing COD_TEMPLATE.
        Joins chunks with newlines as context.

        Args:
            context_chunks: List of text chunks to be summarized.
            current_level: The hierarchical level of the summary being generated.
                           Must be non-negative.

        Returns:
            The formatted prompt string ready to be sent to the LLM.

        Raises:
            ValueError: If current_level is negative.
        """
        if current_level < 0:
            msg = f"Invalid level: {current_level}. Level must be non-negative."
            raise ValueError(msg)

        # Matome usually handles list of chunks by joining them.
        context = "\n\n".join(context_chunks)
        return COD_TEMPLATE.format(context=context)

    def parse_output(self, llm_output: str) -> str:
        """
        Parses the raw LLM output into the final summary string.

        Returns the output as-is, matching legacy behavior.

        Args:
            llm_output: The raw string output from the LLM.

        Returns:
            The parsed summary string.
        """
        return llm_output
