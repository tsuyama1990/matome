from typing import Self

from pydantic import BaseModel, ConfigDict, Field


class ProcessingConfig(BaseModel):
    """Configuration for text processing and chunking."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    # Chunking Configuration
    max_tokens: int = Field(default=500, ge=1, description="Maximum number of tokens per chunk.")
    overlap: int = Field(
        default=0, ge=0, description="Number of overlapping tokens between chunks."
    )
    tokenizer_model: str = Field(
        default="cl100k_base", description="Tokenizer model/encoding name to use."
    )

    # Semantic Chunking Configuration
    semantic_chunking_mode: bool = Field(
        default=False, description="Whether to use semantic chunking instead of token chunking."
    )
    semantic_chunking_threshold: float = Field(
        default=0.8, ge=0.0, le=1.0, description="Cosine similarity threshold for merging sentences."
    )
    semantic_chunking_percentile: int = Field(
        default=90, ge=0, le=100, description="Percentile threshold for breakpoint detection (if using percentile mode)."
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
    max_retries: int = Field(
        default=3, ge=0, description="Maximum number of retries for LLM calls."
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
