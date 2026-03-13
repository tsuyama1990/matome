class ProcessingError(Exception):
    """Exception raised when an error occurs during document processing."""


class DocumentNotFoundError(ProcessingError):
    """Exception raised when a document cannot be found."""


class ConfigurationError(ProcessingError):
    """Exception raised when configuration is invalid or missing."""


class LLMAPIError(ProcessingError):
    """Exception raised when an external LLM API call fails."""


class DependencyError(ProcessingError):
    """Exception raised when a dependency cannot be resolved."""
