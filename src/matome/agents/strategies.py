from matome.utils.prompts import COD_TEMPLATE


class BaseSummaryStrategy:
    """
    Default strategy using Chain of Density (CoD) or standard summarization.
    """

    def format_prompt(self, text: str, existing_summary: str | None = None) -> str:
        """Format the prompt using the default Chain of Density template."""
        # COD_TEMPLATE expects {context}
        return COD_TEMPLATE.format(context=text)


class WisdomStrategy:
    """
    Strategy for generating Wisdom (L1) - Abstract, Philosophical, Concise.
    """

    def format_prompt(self, text: str, existing_summary: str | None = None) -> str:
        """Format the prompt for Wisdom generation."""
        return (
            "You are a wise philosopher. Distill the following text into a single, profound aphorism or truth. "
            "Capture the 'Soul' of the document.\n"
            "Constraints:\n"
            "- Length: 20-50 characters.\n"
            "- No bullet points.\n"
            "- Abstract concepts only.\n\n"
            f"Text:\n{text}"
        )


class KnowledgeStrategy:
    """
    Strategy for generating Knowledge (L2) - Structural, Explanatory.
    """

    def format_prompt(self, text: str, existing_summary: str | None = None) -> str:
        """Format the prompt for Knowledge generation."""
        return (
            "You are a systems thinker. Identify the underlying mental models, frameworks, and mechanisms in the text. "
            "Explain 'Why' and 'How it works' rather than just listing facts.\n"
            "Constraints:\n"
            "- Focus on relationships and structure.\n"
            "- Use clear headings for key concepts.\n\n"
            f"Text:\n{text}"
        )


class InformationStrategy:
    """
    Strategy for generating Information (L3) - Actionable, Concrete.
    """

    def format_prompt(self, text: str, existing_summary: str | None = None) -> str:
        """Format the prompt for Information generation."""
        return (
            "You are an operations manager. Convert this text into a concrete action plan, checklist, or set of specific steps. "
            "Focus on 'What to do'.\n"
            "Constraints:\n"
            "- Use bullet points or numbered lists.\n"
            "- Be specific and actionable.\n\n"
            f"Text:\n{text}"
        )
