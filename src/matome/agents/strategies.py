from typing import Protocol

from domain_models.metadata import DIKWLevel
from matome.utils.prompts import (
    ACTION_PROMPT,
    COD_TEMPLATE,
    KNOWLEDGE_PROMPT,
    WISDOM_PROMPT,
)


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


class ActionStrategy:
    """
    Strategy for generating Level 1 (Information/Action) summaries.
    Focuses on actionable steps and rules.
    """

    def create_prompt(self, context_chunks: list[str], current_level: int) -> str:
        context_text = "\n\n".join(context_chunks)
        return ACTION_PROMPT.format(context=context_text)

    def parse_output(self, llm_output: str) -> str:
        return llm_output


class RefinementStrategy:
    """
    Strategy for refining a node based on user instructions.
    """

    def __init__(self, instruction: str) -> None:
        self.instruction = instruction

    def create_prompt(self, context_chunks: list[str], current_level: int) -> str:
        text = "\n\n".join(context_chunks)
        return f"""
Refine the following content based on the user instruction.

Content:
{text}

Instruction:
{self.instruction}

Output:
The refined content.
"""

    def parse_output(self, llm_output: str) -> str:
        return llm_output


class KnowledgeStrategy:
    """
    Strategy for generating Level 2 (Knowledge) summaries.
    Focuses on mechanisms and frameworks.
    """

    def create_prompt(self, context_chunks: list[str], current_level: int) -> str:
        context_text = "\n\n".join(context_chunks)
        return KNOWLEDGE_PROMPT.format(context=context_text)

    def parse_output(self, llm_output: str) -> str:
        return llm_output


class WisdomStrategy:
    """
    Strategy for generating Level 3+ (Wisdom) summaries.
    Focuses on core philosophy and single-message insights.
    """

    def create_prompt(self, context_chunks: list[str], current_level: int) -> str:
        context_text = "\n\n".join(context_chunks)
        return WISDOM_PROMPT.format(context=context_text)

    def parse_output(self, llm_output: str) -> str:
        return llm_output


class DIKWHierarchyStrategy:
    """
    Composite strategy that delegates to specific DIKW strategies based on the tree level.
    """

    def __init__(self) -> None:
        self.strategies: dict[DIKWLevel, PromptStrategy] = {
            DIKWLevel.INFORMATION: ActionStrategy(),
            DIKWLevel.KNOWLEDGE: KnowledgeStrategy(),
            DIKWLevel.WISDOM: WisdomStrategy(),
        }
        self.default_strategy = WisdomStrategy()

    def create_prompt(self, context_chunks: list[str], current_level: int) -> str:
        # Select strategy based on DIKW level.
        dikw_level = DIKWLevel.from_level(current_level)
        strategy = self.strategies.get(dikw_level, self.default_strategy)

        return strategy.create_prompt(context_chunks, current_level)

    def parse_output(self, llm_output: str) -> str:
        # Parsing logic is typically uniform, but we delegate just in case.
        # Since we don't know the level here, we rely on the fact that currently
        # all strategies use identity parsing.
        return llm_output
