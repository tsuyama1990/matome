"""Custom domain exceptions."""


class ProcessingError(Exception):
    """Raised when an error occurs during processing."""


class LLMError(Exception):
    """Raised when an error occurs interacting with the LLM gateway."""
