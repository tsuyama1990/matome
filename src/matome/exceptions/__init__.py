class MatomeError(Exception):
    """Base exception for Matome."""


class SummarizationError(MatomeError):
    """Raised when summarization fails."""


class StoreError(MatomeError):
    """Raised when storage operations fail."""


class RefinementError(MatomeError):
    """Raised when interactive refinement fails."""
