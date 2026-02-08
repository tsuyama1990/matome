from typing import Self

from pydantic import BaseModel, ConfigDict, Field


class ProcessingConfig(BaseModel):
    """Configuration for text processing and chunking."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    max_tokens: int = Field(default=500, ge=1, description="Maximum number of tokens per chunk.")
    overlap: int = Field(
        default=0, ge=0, description="Number of overlapping tokens between chunks."
    )
    tokenizer_model: str = Field(
        default="cl100k_base", description="Tokenizer model/encoding name to use."
    )

    # Embedding Configuration
    embedding_model: str = Field(
        default="intfloat/multilingual-e5-large", description="HuggingFace model name for embeddings."
    )
    embedding_batch_size: int = Field(
        default=32, ge=1, description="Batch size for embedding generation."
    )

    # Clustering Configuration
    clustering_algorithm: str = Field(
        default="gmm", description="Algorithm to use (e.g., 'gmm'). Currently only 'gmm' is supported."
    )
    n_clusters: int | None = Field(
        default=None, description="Fixed number of clusters (if applicable)."
    )
    random_state: int = Field(
        default=42, description="Random seed for reproducibility."
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
        Returns the default configuration using Pydantic defaults.
        """
        return cls()

    @classmethod
    def high_precision(cls) -> Self:
        """
        Returns a configuration optimized for higher precision (smaller chunks).
        """
        return cls(max_tokens=200, overlap=20)
