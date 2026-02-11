from typing import Protocol

from matome.utils.prompts import COD_TEMPLATE


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
    A default implementation that mimics the current "generic summary" logic,
    ensuring the system remains functional during the transition.
    """

    def create_prompt(self, context_chunks: list[str], current_level: int) -> str:
        """
        Constructs the LLM prompt based on the context and tree level.
        Uses the legacy Chain of Density template.
        """
        # Join chunks with double newlines if multiple are provided
        context_text = "\n\n".join(context_chunks)
        return COD_TEMPLATE.format(context=context_text)

    def parse_output(self, llm_output: str) -> str:
        """
        Parses the raw LLM output into the final summary string.
        Passthrough implementation for base strategy.
        """
        return llm_output
