from typing import Any

from src.interfaces import LLMError, LLMProtocol


class DefaultLLMProtocol(LLMProtocol):
    """Production implementation of the LLMProtocol."""

    def invoke(self, prompt: str, timeout: int = 30, retries: int = 3, **kwargs: Any) -> str:
        """Invokes the LLM with a prompt and returns the string response."""
        # This is a placeholder for the actual API call logic in Cycle 02.
        if not prompt:
            msg = "Prompt cannot be empty"
            raise LLMError(msg)

        return f"LLM simulated response for: {prompt[:20]}..."
