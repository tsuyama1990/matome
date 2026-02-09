import os
from enum import Enum
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, field_validator

# Define strict defaults here to isolate them
# These are fallback values if Env Vars are not present
DEFAULT_TOKENIZER = "cl100k_base"
DEFAULT_EMBEDDING = "intfloat/multilingual-e5-large"
DEFAULT_SUMMARIZER = "gpt-4o"

# Allowed tokenizer models for security whitelist
ALLOWED_TOKENIZER_MODELS = {
    "cl100k_base",
    "p50k_base",
    "r50k_base",
    "gpt2",
    "gpt-3.5-turbo",
    "gpt-4",
    "gpt-4o",
    "text-embedding-ada-002",
    "text-embedding-3-small",
    "text-embedding-3-large",
}


class ClusteringAlgorithm(Enum):
    GMM = "gmm"


class ProcessingConfig(BaseModel):
    """
    Configuration for text processing and chunking.

    Defaults are defined directly in the model or via default_factory using os.getenv.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    # Chunking Configuration
    max_tokens: int = Field(default=500, ge=1, description="Maximum number of tokens per chunk.")
    overlap: int = Field(
        default=0, ge=0, description="Number of overlapping tokens between chunks."
    )
    tokenizer_model: str = Field(
        default_factory=lambda: os.getenv("TOKENIZER_MODEL", DEFAULT_TOKENIZER),
        description="Tokenizer model/encoding name to use.",
    )

    # Semantic Chunking Configuration
    semantic_chunking_mode: bool = Field(
        default=False, description="Whether to use semantic chunking instead of token chunking."
    )
    semantic_chunking_threshold: float = Field(
        default=0.8,
        ge=0.0,
        le=1.0,
        description="Cosine similarity threshold for merging sentences.",
    )
    semantic_chunking_percentile: int = Field(
        default=90,
        ge=0,
        le=100,
        description="Percentile threshold for breakpoint detection (if using percentile mode).",
    )

    # Embedding Configuration
    embedding_model: str = Field(
        default_factory=lambda: os.getenv("EMBEDDING_MODEL", DEFAULT_EMBEDDING),
        description="HuggingFace model name for embeddings.",
    )
    embedding_batch_size: int = Field(
        default=32, ge=1, description="Batch size for embedding generation."
    )

    # Clustering Configuration
    clustering_algorithm: ClusteringAlgorithm = Field(
        default=ClusteringAlgorithm.GMM,
        description="Algorithm to use (e.g., 'gmm'). Currently only 'gmm' is supported.",
    )
    n_clusters: int | None = Field(
        default=None, description="Fixed number of clusters (if applicable)."
    )
    random_state: int = Field(default=42, description="Random seed for reproducibility.")
    umap_n_neighbors: int = Field(
        default=15,
        ge=2,
        description="UMAP parameter: Number of neighbors for dimensionality reduction.",
    )
    umap_min_dist: float = Field(
        default=0.1, ge=0.0, description="UMAP parameter: Minimum distance between points."
    )
    umap_n_components: int = Field(
        default=2, ge=2, description="UMAP parameter: Number of dimensions to reduce to."
    )
    write_batch_size: int = Field(
        default=10_000,
        ge=1,
        description="Batch size for writing vectors to disk during clustering.",
    )

    # Summarization Configuration
    summarization_model: str = Field(
        default_factory=lambda: os.getenv("SUMMARIZATION_MODEL", DEFAULT_SUMMARIZER),
        description="Model to use for summarization.",
    )
    max_summary_tokens: int = Field(
        default=200, ge=1, description="Target token count for summaries."
    )
    max_retries: int = Field(
        default=3, ge=0, description="Maximum number of retries for LLM calls."
    )
    llm_temperature: float = Field(
        default=0.0, ge=0.0, le=1.0, description="Sampling temperature for LLM."
    )
    max_word_length: int = Field(
        default=1000, ge=100, description="Maximum length of a single word for input validation."
    )
    max_input_length: int = Field(
        default=500_000, ge=100, description="Maximum length of input text for summarization."
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

    @field_validator("tokenizer_model")
    @classmethod
    def validate_tokenizer_model(cls, v: str) -> str:
        """Validate tokenizer model against whitelist."""
        if v not in ALLOWED_TOKENIZER_MODELS:
            msg = (
                f"Tokenizer model '{v}' is not allowed. "
                f"Allowed: {sorted(ALLOWED_TOKENIZER_MODELS)}"
            )
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
