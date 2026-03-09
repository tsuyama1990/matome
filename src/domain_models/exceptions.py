class RepositoryError(Exception):
    """Base exception for all repository-related errors."""


class AIServiceError(Exception):
    """Base exception for external AI service failures."""


class ConfigurationError(Exception):
    """Exception for invalid or missing configuration parameters."""
