"""
Custom exceptions for the Matome system.
"""

class MatomeError(Exception):
    """Base exception for Matome system."""

class SummarizationError(MatomeError):
    """Raised when summarization fails."""
