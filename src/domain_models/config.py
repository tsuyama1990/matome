import os
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, field_validator

from domain_models.constants import (
    DEFAULT_CLUSTERING_ALGORITHM,
    DEFAULT_EMBEDDING_BATCH_SIZE,
    DEFAULT_EMBEDDING_MODEL,
    DEFAULT_MAX_RETRIES,
    DEFAULT_MAX_SUMMARY_TOKENS,
    DEFAULT_MAX_TOKENS,
    DEFAULT_N_CLUSTERS,
    DEFAULT_OVERLAP,
    DEFAULT_RANDOM_STATE,
    DEFAULT_SEMANTIC_CHUNKING_MODE,
    DEFAULT_SEMANTIC_CHUNKING_PERCENTILE,
    DEFAULT_SEMANTIC_CHUNKING_THRESHOLD,
    DEFAULT_SUMMARIZATION_MODEL,
    DEFAULT_TOKENIZER_MODEL,
    DEFAULT_UMAP_MIN_DIST,
    DEFAULT_UMAP_N_NEIGHBORS,
)


class ProcessingConfig(BaseModel):
    """
    Configuration for text processing and chunking.

    Environment variables (e.g., TOKENIZER_MODEL, EMBEDDING_MODEL) override defaults
    from `matome.utils.constants`.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    # Chunking Configuration
    max_tokens: int = Field(default=DEFAULT_MAX_TOKENS, ge=1, description="Maximum number of tokens per chunk.")
    overlap: int = Field(
        default=DEFAULT_OVERLAP, ge=0, description="Number of overlapping tokens between chunks."
    )
    tokenizer_model: str = Field(
        default_factory=lambda: os.getenv("TOKENIZER_MODEL", DEFAULT_TOKENIZER_MODEL),
        description="Tokenizer model/encoding name to use."
    )

    # Semantic Chunking Configuration
    semantic_chunking_mode: bool = Field(
        default=DEFAULT_SEMANTIC_CHUNKING_MODE, description="Whether to use semantic chunking instead of token chunking."
    )
    semantic_chunking_threshold: float = Field(
        default=DEFAULT_SEMANTIC_CHUNKING_THRESHOLD, ge=0.0, le=1.0, description="Cosine similarity threshold for merging sentences."
    )
    semantic_chunking_percentile: int = Field(
        default=DEFAULT_SEMANTIC_CHUNKING_PERCENTILE, ge=0, le=100, description="Percentile threshold for breakpoint detection (if using percentile mode)."
    )

    # Embedding Configuration
    embedding_model: str = Field(
        default_factory=lambda: os.getenv("EMBEDDING_MODEL", DEFAULT_EMBEDDING_MODEL),
        description="HuggingFace model name for embeddings."
    )
    embedding_batch_size: int = Field(
        default=DEFAULT_EMBEDDING_BATCH_SIZE, ge=1, description="Batch size for embedding generation."
    )

    # Clustering Configuration
    clustering_algorithm: str = Field(
        default=DEFAULT_CLUSTERING_ALGORITHM, description="Algorithm to use (e.g., 'gmm'). Currently only 'gmm' is supported."
    )
    n_clusters: int | None = Field(
        default=DEFAULT_N_CLUSTERS, description="Fixed number of clusters (if applicable)."
    )
    random_state: int = Field(
        default=DEFAULT_RANDOM_STATE, description="Random seed for reproducibility."
    )
    umap_n_neighbors: int = Field(
        default=DEFAULT_UMAP_N_NEIGHBORS, ge=2, description="UMAP parameter: Number of neighbors for dimensionality reduction."
    )
    umap_min_dist: float = Field(
        default=DEFAULT_UMAP_MIN_DIST, ge=0.0, description="UMAP parameter: Minimum distance between points."
    )

    # Summarization Configuration
    summarization_model: str = Field(
        default_factory=lambda: os.getenv("SUMMARIZATION_MODEL", DEFAULT_SUMMARIZATION_MODEL),
        description="Model to use for summarization."
    )
    max_summary_tokens: int = Field(
        default=DEFAULT_MAX_SUMMARY_TOKENS, ge=1, description="Target token count for summaries."
    )
    max_retries: int = Field(
        default=DEFAULT_MAX_RETRIES, ge=0, description="Maximum number of retries for LLM calls."
    )

    @field_validator("embedding_model")
    @classmethod
    def validate_embedding_model(cls, v: str) -> str:
        """Validate embedding model name to prevent potential issues."""
        if not v or not v.strip():
            msg = "Embedding model name cannot be empty."
            raise ValueError(msg)
        # Basic check for suspicious characters
        forbidden = [";", "&", "|", "`", "$", "(", ")", "<", ">"]
        if any(char in v for char in forbidden):
            msg = f"Invalid characters in embedding model name: {v}"
            raise ValueError(msg)
        return v

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
