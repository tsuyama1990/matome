import typing


class LLMProtocol(typing.Protocol):
    """Abstract protocol defining the required capabilities of an LLM provider."""

    async def generate_text(self, prompt: str, model: str) -> str:
        """
        Generates text based on the given prompt and model.

        Args:
            prompt (str): The prompt to send to the LLM.
            model (str): The model identifier to use.

        Returns:
            str: The generated text response.
        """
        ...
