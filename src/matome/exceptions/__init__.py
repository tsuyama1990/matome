"""
Custom exceptions for the Matome system.
"""

class MatomeError(Exception):
    """
    Base exception for Matome system.
    All custom exceptions in the system should inherit from this.
    """

class SummarizationError(MatomeError):
    """
    Raised when summarization fails.

    This error encapsulates failures during the summarization process,
    such as API connection issues, missing configuration, or parsing errors.
    """
