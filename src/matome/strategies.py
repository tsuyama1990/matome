import logging
from typing import Any

from domain_models.data_schema import DIKWLevel, NodeMetadata
from matome.interfaces import PromptStrategy
from matome.utils.prompts import COD_TEMPLATE

logger = logging.getLogger(__name__)


class BaseSummaryStrategy(PromptStrategy):
    """
    Base strategy for summarization.
    """

    def format_prompt(self, text: str | list[str], context: dict[str, Any] | None = None) -> str:
        """
        Format the prompt. By default, joins text and uses a simple template or override.
        """
        text_str = "\n\n".join(text) if isinstance(text, list) else text
        prompt = f"Summarize the following text:\n\n{text_str}"

        if context and context.get("instruction"):
            prompt += f"\n\nUser Instruction: {context['instruction']}"

        return prompt

    def parse_output(self, response: str) -> dict[str, Any]:
        """
        Parse the output. By default, returns the raw response as 'text'.
        """
        return {"text": response.strip(), "metadata": NodeMetadata(dikw_level=DIKWLevel.DATA)}


class DefaultStrategy(BaseSummaryStrategy):
    """
    Default Chain of Density strategy.
    """

    def format_prompt(self, text: str | list[str], context: dict[str, Any] | None = None) -> str:
        text_str = "\n\n".join(text) if isinstance(text, list) else text
        base_prompt = COD_TEMPLATE.format(context=text_str)

        if context and context.get("instruction"):
            base_prompt += f"\n\nUser Instruction: {context['instruction']}"

        return base_prompt

    def parse_output(self, response: str) -> dict[str, Any]:
        # Simple cleanup, CoD usually outputs text.
        return {
            "text": response.strip(),
            "metadata": NodeMetadata(dikw_level=DIKWLevel.DATA) # Default to DATA
        }


class WisdomStrategy(BaseSummaryStrategy):
    """
    L1: Wisdom - Philosophical, Aphorism, 20-40 chars.
    """

    def format_prompt(self, text: str | list[str], context: dict[str, Any] | None = None) -> str:
        text_str = "\n\n".join(text) if isinstance(text, list) else text
        prompt = f"""
        Analyze the following text and distill it into a single piece of **Wisdom** (L1).

        Input Text:
        {text_str}

        Requirements:
        1. Context: Strip away all context. Focus on universal truth.
        2. Format: Aphorism, proverb, or philosophical statement.
        3. Length: Extremely concise (20-40 characters ideally, max 60).
        4. Goal: Provide a "One Message" takeaway.

        Output ONLY the wisdom statement.
        """

        if context and context.get("instruction"):
            prompt += f"\n\nUser Instruction: {context['instruction']}"

        return prompt

    def parse_output(self, response: str) -> dict[str, Any]:
        return {
            "text": response.strip(),
            "metadata": NodeMetadata(dikw_level=DIKWLevel.WISDOM)
        }


class KnowledgeStrategy(BaseSummaryStrategy):
    """
    L2: Knowledge - Frameworks, Mechanisms, "Why".
    """

    def format_prompt(self, text: str | list[str], context: dict[str, Any] | None = None) -> str:
        text_str = "\n\n".join(text) if isinstance(text, list) else text
        prompt = f"""
        Analyze the following text and extract the **Knowledge** (L2) structure.

        Input Text:
        {text_str}

        Requirements:
        1. Focus: Identification of frameworks, mental models, or mechanisms.
        2. Explanation: Explain "Why this is true" or "How the system works".
        3. Format: Conceptual explanation. Avoid specific examples (save for lower levels).
        4. Tone: Analytical, structural.

        Output the knowledge explanation.
        """

        if context and context.get("instruction"):
            prompt += f"\n\nUser Instruction: {context['instruction']}"

        return prompt

    def parse_output(self, response: str) -> dict[str, Any]:
        return {
            "text": response.strip(),
            "metadata": NodeMetadata(dikw_level=DIKWLevel.KNOWLEDGE)
        }


class InformationStrategy(BaseSummaryStrategy):
    """
    L3: Information - Actionable, How-to, Checklists.
    """

    def format_prompt(self, text: str | list[str], context: dict[str, Any] | None = None) -> str:
        text_str = "\n\n".join(text) if isinstance(text, list) else text
        prompt = f"""
        Analyze the following text and convert it into **Information** (L3).

        Input Text:
        {text_str}

        Requirements:
        1. Focus: Actionable steps, rules, procedures, or checklists.
        2. Usability: Must be immediately usable by the reader (How-to).
        3. Format: Bullet points, numbered lists, or clear instructions.
        4. Specificity: High.

        Output the actionable information.
        """

        if context and context.get("instruction"):
            prompt += f"\n\nUser Instruction: {context['instruction']}"

        return prompt

    def parse_output(self, response: str) -> dict[str, Any]:
        return {
            "text": response.strip(),
            "metadata": NodeMetadata(dikw_level=DIKWLevel.INFORMATION)
        }
