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
    """

    def create_prompt(self, context_chunks: list[str], current_level: int) -> str:
        """
        Uses the existing COD_TEMPLATE.
        Joins chunks with newlines (or spaces) as context.
        """
        # Matome usually handles list of chunks by joining them.
        # existing SummarizationAgent.summarize(text: str) -> COD_TEMPLATE.format(context=safe_text)
        # So we should join context_chunks.
        context = "\n\n".join(context_chunks)
        return COD_TEMPLATE.format(context=context)

    def parse_output(self, llm_output: str) -> str:
        """
        Returns the output as-is, matching legacy behavior.
        """
        return llm_output
