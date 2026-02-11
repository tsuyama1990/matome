import os
from enum import Enum, StrEnum
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from domain_models.constants import (
    ALLOWED_EMBEDDING_MODELS,
    ALLOWED_SUMMARIZATION_MODELS,
    ALLOWED_TOKENIZER_MODELS,
    DEFAULT_EMBEDDING,
    DEFAULT_SUMMARIZER,
    DEFAULT_TOKENIZER,
    LARGE_SCALE_THRESHOLD,
)


class ClusteringAlgorithm(Enum):
    GMM = "gmm"


class ProcessingMode(StrEnum):
    """Mode of processing for the pipeline."""

    DEFAULT = "default"
    DIKW = "dikw"


def _safe_getenv(key: str, default: str) -> str:
    """Safely get environment variable with fallback."""
    val = os.getenv(key)
    if val is None or not val.strip():
        return default
    return val


class ProcessingConfig(BaseModel):
    """
    Configuration for text processing and chunking.

    Defaults are defined directly in the model or via default_factory using os.getenv.
    Securely handles environment variables.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    # Chunking Configuration
    max_tokens: int = Field(default=500, ge=1, description="Maximum number of tokens per chunk.")
    overlap: int = Field(
        default=0, ge=0, description="Number of overlapping tokens between chunks."
    )
    tokenizer_model: str = Field(
        default_factory=lambda: _safe_getenv("TOKENIZER_MODEL", DEFAULT_TOKENIZER),
        description="Tokenizer model/encoding name to use.",
    )

    # Processing Mode
    processing_mode: ProcessingMode = Field(
        default=ProcessingMode.DEFAULT,
        description="Mode of processing: 'default' (standard summarization) or 'dikw' (Data-Information-Knowledge-Wisdom hierarchy).",
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
        default_factory=lambda: _safe_getenv("EMBEDDING_MODEL", DEFAULT_EMBEDDING),
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
        default=1000,
        ge=1,
        description="Batch size for writing vectors to disk during clustering.",
    )
    clustering_probability_threshold: float = Field(
        default=0.1,
        ge=0.0,
        le=1.0,
        description="Minimum probability for assigning a node to a cluster (soft clustering).",
    )
    large_scale_threshold: int = Field(
        default=LARGE_SCALE_THRESHOLD,
        ge=1,
        description="Threshold for switching to approximate clustering.",
    )
    chunk_buffer_size: int = Field(
        default=50,
        ge=1,
        description="Buffer size for batch database writes in Raptor engine.",
    )
    canvas_node_width: int = Field(
        default=400,
        ge=10,
        le=5000,
        description="Width of nodes in Obsidian Canvas export.",
    )
    canvas_node_height: int = Field(
        default=200,
        ge=10,
        le=5000,
        description="Height of nodes in Obsidian Canvas export.",
    )
    canvas_gap_x: int = Field(
        default=50,
        ge=0,
        le=2000,
        description="Horizontal gap between nodes in Obsidian Canvas export.",
    )
    canvas_gap_y: int = Field(
        default=300,
        ge=0,
        le=2000,
        description="Vertical gap between nodes in Obsidian Canvas export.",
    )

    # Summarization Configuration
    summarization_model: str = Field(
        default_factory=lambda: _safe_getenv("SUMMARIZATION_MODEL", DEFAULT_SUMMARIZER),
        description="Model to use for summarization.",
    )
    max_summary_tokens: int = Field(
        default=200, ge=1, description="Target token count for summaries."
    )
    max_retries: int = Field(
        default=3, ge=0, description="Maximum number of retries for LLM calls."
    )
    retry_multiplier: float = Field(
        default=1.0, ge=0.1, description="Exponential backoff multiplier."
    )
    retry_min_wait: int = Field(
        default=2, ge=0, description="Minimum wait time between retries (seconds)."
    )
    retry_max_wait: int = Field(
        default=10, ge=0, description="Maximum wait time between retries (seconds)."
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

    # Verification Configuration
    verifier_enabled: bool = Field(
        default=True, description="Whether to perform verification after summarization."
    )
    verification_model: str = Field(
        default_factory=lambda: _safe_getenv("VERIFICATION_MODEL", DEFAULT_SUMMARIZER),
        description="Model to use for verification (defaults to summarization model).",
    )

    @field_validator("embedding_model", mode="after")
    @classmethod
    def validate_embedding_model(cls, v: str) -> str:
        """Validate embedding model name to prevent potential issues."""
        if not v or not v.strip():
            msg = "Embedding model name cannot be empty."
            raise ValueError(msg)
        if v not in ALLOWED_EMBEDDING_MODELS:
            msg = (
                f"Embedding model '{v}' is not in the allowed list. "
                f"Allowed: {sorted(ALLOWED_EMBEDDING_MODELS)}"
            )
            raise ValueError(msg)
        return v

    @field_validator("summarization_model", "verification_model", mode="after")
    @classmethod
    def validate_llm_model(cls, v: str) -> str:
        """Validate LLM model name against whitelist."""
        if v not in ALLOWED_SUMMARIZATION_MODELS:
            msg = f"LLM model '{v}' is not allowed. Allowed: {sorted(ALLOWED_SUMMARIZATION_MODELS)}"
            raise ValueError(msg)
        return v

    @field_validator("tokenizer_model", mode="after")
    @classmethod
    def validate_tokenizer_model(cls, v: str) -> str:
        """Validate tokenizer model against whitelist."""
        if not v or not v.strip():
            msg = "Tokenizer model name cannot be empty."
            raise ValueError(msg)
        if v not in ALLOWED_TOKENIZER_MODELS:
            msg = (
                f"Tokenizer model '{v}' is not allowed. Allowed: {sorted(ALLOWED_TOKENIZER_MODELS)}"
            )
            raise ValueError(msg)
        return v

    @model_validator(mode="after")
    def validate_clustering_config(self) -> Self:
        """Ensure n_clusters consistency with algorithm."""
        # If n_clusters is provided, it must be at least 2 for GMM to work meaningfully.
        # While 1 cluster is a fallback logic in engine, configuration should ideally not request invalid states.
        # But wait, 1 cluster is valid if we just want to group everything.
        # However, scikit-learn GMM requires n_components >= 1.
        # If the user sets n_clusters=0 or negative, that's invalid.
        if self.n_clusters is not None and self.n_clusters < 1:
            msg = f"n_clusters must be at least 1 (got {self.n_clusters})."
            raise ValueError(msg)
        return self

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
