from typing import Any, Protocol, runtime_checkable

from matome.utils.prompts import COD_TEMPLATE


@runtime_checkable
class PromptStrategy(Protocol):
    """
    Protocol defining how to generate prompts and parse responses.
    """

    def generate_prompt(self, context: str, **kwargs: Any) -> str:
        """
        Create the prompt string for the LLM.
        """
        ...

    def parse_response(self, response: str) -> str:
        """
        Parse the LLM response (e.g., remove Chain-of-Thought, extract JSON).
        """
        ...


class BaseSummaryStrategy:
    """
    Legacy strategy implementing Chain of Density (CoD).
    """

    def generate_prompt(self, context: str, **kwargs: Any) -> str:
        """Generate a summary prompt using COD_TEMPLATE."""
        return COD_TEMPLATE.format(context=context)

    def parse_response(self, response: str) -> str:
        """Parse the response by stripping whitespace."""
        return response.strip()
