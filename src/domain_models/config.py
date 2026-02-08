from typing import Self

from pydantic import BaseModel, ConfigDict, Field


class ProcessingConfig(BaseModel):
    """Configuration for text processing and chunking."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    max_tokens: int = Field(default=500, ge=1, description="Maximum number of tokens per chunk.")
    overlap: int = Field(
        default=0, ge=0, description="Number of overlapping tokens between chunks."
    )

    # Clustering Configuration
    clustering_algorithm: str = Field(
        default="gmm", description="Algorithm to use (e.g., 'gmm', 'agglomerative')."
    )
    n_clusters: int | None = Field(
        default=None, description="Fixed number of clusters (if applicable)."
    )

    # Summarization Configuration
    summarization_model: str = Field(
        default="gpt-4o", description="Model to use for summarization."
    )
    max_summary_tokens: int = Field(
        default=200, ge=1, description="Target token count for summaries."
    )

    @classmethod
    def default(cls) -> Self:
        """
        Returns the default configuration.

        Defaults:
            max_tokens: 500
            overlap: 0
            clustering: gmm
            summarization: gpt-4o
        """
        return cls(max_tokens=500, overlap=0)

    @classmethod
    def high_precision(cls) -> Self:
        """
        Returns a configuration optimized for higher precision (smaller chunks).

        Defaults:
            max_tokens: 200
            overlap: 20
        """
        return cls(max_tokens=200, overlap=20)
