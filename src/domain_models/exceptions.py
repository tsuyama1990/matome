class ProcessingError(Exception):
    """Exception raised when an error occurs during document processing."""


class RaptorError(Exception):
    """Exception raised when an error occurs during RAPTOR generation."""


class NLPModelLoadError(Exception):
    """Exception raised when the NLP model fails to load."""
