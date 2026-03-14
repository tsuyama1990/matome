class ProcessingError(Exception):
    """Exception raised when an error occurs during document processing."""


class RaptorError(Exception):
    """Exception raised when an error occurs during RAPTOR generation."""


class NLPModelLoadError(Exception):
    """Exception raised when the NLP model fails to load."""


class LLMConnectionError(Exception):
    """Exception raised when a network error occurs during LLM communication."""


class LLMAuthenticationError(Exception):
    """Exception raised when authentication fails during LLM communication."""
