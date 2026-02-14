import os
from enum import Enum
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from domain_models.constants import (
    ALLOWED_EMBEDDING_MODELS,
    ALLOWED_SUMMARIZATION_MODELS,
    ALLOWED_TOKENIZER_MODELS,
    DEFAULT_CANVAS_GAP_X,
    DEFAULT_CANVAS_GAP_Y,
    DEFAULT_CANVAS_NODE_HEIGHT,
    DEFAULT_CANVAS_NODE_WIDTH,
    DEFAULT_CHUNK_BUFFER_SIZE,
    DEFAULT_CLUSTER_BATCH_SIZE,
    DEFAULT_CLUSTERING_PROBABILITY_THRESHOLD,
    DEFAULT_CLUSTERING_WRITE_BATCH_SIZE,
    DEFAULT_EMBEDDING,
    DEFAULT_EMBEDDING_BATCH_SIZE,
    DEFAULT_LLM_TEMPERATURE,
    DEFAULT_MAX_FILE_SIZE_BYTES,
    DEFAULT_MAX_INPUT_LENGTH,
    DEFAULT_MAX_INSTRUCTION_LENGTH,
    DEFAULT_MAX_RETRIES,
    DEFAULT_MAX_SUMMARY_TOKENS,
    DEFAULT_MAX_TOKENS,
    DEFAULT_MAX_WORD_LENGTH,
    DEFAULT_OVERLAP,
    DEFAULT_RANDOM_STATE,
    DEFAULT_SEMANTIC_CHUNKING_MODE,
    DEFAULT_SEMANTIC_CHUNKING_PERCENTILE,
    DEFAULT_SEMANTIC_CHUNKING_THRESHOLD,
    DEFAULT_SERVER_PORT,
    DEFAULT_STORE_READ_BATCH_SIZE,
    DEFAULT_STORE_WRITE_BATCH_SIZE,
    DEFAULT_STRATEGY_MAPPING,
    DEFAULT_SUMMARIZER,
    DEFAULT_TOKENIZER,
    DEFAULT_UMAP_MIN_DIST,
    DEFAULT_UMAP_N_COMPONENTS,
    DEFAULT_UMAP_N_NEIGHBORS,
    DEFAULT_VERIFIER_ENABLED,
    HIGH_PRECISION_MAX_TOKENS,
    HIGH_PRECISION_OVERLAP,
    LARGE_SCALE_THRESHOLD,
)
from domain_models.types import DIKWLevel


class ClusteringAlgorithm(Enum):
    GMM = "gmm"


def _safe_getenv(key: str, default: str) -> str:
    """Safely get environment variable with fallback."""
    val = os.getenv(key)
    if val is None or not val.strip():
        return default
    return val

def _validate_model_name(value: str, allowed: set[str], name: str) -> str:
    """Helper to validate model names against whitelist."""
    if value not in allowed:
        msg = f"{name} '{value}' is not allowed. Allowed: {sorted(allowed)}"
        raise ValueError(msg)
    return value


class ProcessingConfig(BaseModel):
    """
    Configuration for text processing and chunking.

    Defaults are defined directly in the model or via default_factory using os.getenv.
    Securely handles environment variables.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    # Chunking Configuration
    max_tokens: int = Field(default=DEFAULT_MAX_TOKENS, ge=1, description="Maximum number of tokens per chunk.")
    overlap: int = Field(
        default=DEFAULT_OVERLAP, ge=0, description="Number of overlapping tokens between chunks."
    )
    tokenizer_model: str = Field(
        default_factory=lambda: _safe_getenv("TOKENIZER_MODEL", DEFAULT_TOKENIZER),
        description="Tokenizer model/encoding name to use.",
    )

    # Semantic Chunking Configuration
    semantic_chunking_mode: bool = Field(
        default=DEFAULT_SEMANTIC_CHUNKING_MODE, description="Whether to use semantic chunking instead of token chunking."
    )
    semantic_chunking_threshold: float = Field(
        default=DEFAULT_SEMANTIC_CHUNKING_THRESHOLD,
        ge=0.0,
        le=1.0,
        description="Cosine similarity threshold for merging sentences.",
    )
    semantic_chunking_percentile: int = Field(
        default=DEFAULT_SEMANTIC_CHUNKING_PERCENTILE,
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
        default=DEFAULT_EMBEDDING_BATCH_SIZE, ge=1, description="Batch size for embedding generation."
    )

    # Clustering Configuration
    clustering_algorithm: ClusteringAlgorithm = Field(
        default=ClusteringAlgorithm.GMM,
        description="Algorithm to use (e.g., 'gmm'). Currently only 'gmm' is supported.",
    )
    n_clusters: int | None = Field(
        default=None, description="Fixed number of clusters (if applicable)."
    )
    random_state: int = Field(default=DEFAULT_RANDOM_STATE, description="Random seed for reproducibility.")
    umap_n_neighbors: int = Field(
        default=DEFAULT_UMAP_N_NEIGHBORS,
        ge=2,
        description="UMAP parameter: Number of neighbors for dimensionality reduction.",
    )
    umap_min_dist: float = Field(
        default=DEFAULT_UMAP_MIN_DIST, ge=0.0, description="UMAP parameter: Minimum distance between points."
    )
    umap_n_components: int = Field(
        default=DEFAULT_UMAP_N_COMPONENTS, ge=2, description="UMAP parameter: Number of dimensions to reduce to."
    )
    write_batch_size: int = Field(
        default=DEFAULT_CLUSTERING_WRITE_BATCH_SIZE,
        ge=1,
        description="Batch size for writing vectors to disk during clustering.",
    )
    clustering_probability_threshold: float = Field(
        default=DEFAULT_CLUSTERING_PROBABILITY_THRESHOLD,
        ge=0.0,
        le=1.0,
        description="Minimum probability for assigning a node to a cluster (soft clustering).",
    )
    large_scale_threshold: int = Field(
        default=LARGE_SCALE_THRESHOLD,
        ge=1,
        description="Threshold for switching to approximate clustering.",
    )
    cluster_batch_size: int = Field(
        default=DEFAULT_CLUSTER_BATCH_SIZE,
        ge=1,
        description="Batch size for processing clusters during summarization.",
    )
    chunk_buffer_size: int = Field(
        default=DEFAULT_CHUNK_BUFFER_SIZE,
        ge=1,
        description="Buffer size for batch database writes in Raptor engine.",
    )
    canvas_node_width: int = Field(
        default=DEFAULT_CANVAS_NODE_WIDTH,
        ge=10,
        le=5000,
        description="Width of nodes in Obsidian Canvas export.",
    )
    canvas_node_height: int = Field(
        default=DEFAULT_CANVAS_NODE_HEIGHT,
        ge=10,
        le=5000,
        description="Height of nodes in Obsidian Canvas export.",
    )
    canvas_gap_x: int = Field(
        default=DEFAULT_CANVAS_GAP_X,
        ge=0,
        le=2000,
        description="Horizontal gap between nodes in Obsidian Canvas export.",
    )
    canvas_gap_y: int = Field(
        default=DEFAULT_CANVAS_GAP_Y,
        ge=0,
        le=2000,
        description="Vertical gap between nodes in Obsidian Canvas export.",
    )

    # Store Configuration
    store_write_batch_size: int = Field(
        default=DEFAULT_STORE_WRITE_BATCH_SIZE, ge=1, description="Batch size for database write operations."
    )
    store_read_batch_size: int = Field(
        default=DEFAULT_STORE_READ_BATCH_SIZE, ge=1, description="Batch size for database read operations."
    )

    # Interactive Configuration
    max_instruction_length: int = Field(
        default=DEFAULT_MAX_INSTRUCTION_LENGTH, ge=1, description="Maximum length of refinement instructions."
    )
    server_port: int = Field(
        default=DEFAULT_SERVER_PORT, ge=1024, le=65535, description="Default port for the interactive GUI server."
    )
    max_file_size_bytes: int = Field(
        default=DEFAULT_MAX_FILE_SIZE_BYTES, ge=1024, description="Maximum allowed file size for input text."
    )

    # Summarization Configuration
    summarization_model: str = Field(
        default_factory=lambda: _safe_getenv("SUMMARIZATION_MODEL", DEFAULT_SUMMARIZER),
        description="Model to use for summarization.",
    )
    max_summary_tokens: int = Field(
        default=DEFAULT_MAX_SUMMARY_TOKENS, ge=1, description="Target token count for summaries."
    )
    max_retries: int = Field(
        default=DEFAULT_MAX_RETRIES, ge=0, description="Maximum number of retries for LLM calls."
    )
    llm_temperature: float = Field(
        default=DEFAULT_LLM_TEMPERATURE, ge=0.0, le=1.0, description="Sampling temperature for LLM."
    )
    max_word_length: int = Field(
        default=DEFAULT_MAX_WORD_LENGTH, ge=100, description="Maximum length of a single word for input validation."
    )
    max_input_length: int = Field(
        default=DEFAULT_MAX_INPUT_LENGTH, ge=100, description="Maximum length of input text for summarization."
    )

    # Verification Configuration
    verifier_enabled: bool = Field(
        default=DEFAULT_VERIFIER_ENABLED, description="Whether to perform verification after summarization."
    )
    verification_model: str = Field(
        default_factory=lambda: _safe_getenv("VERIFICATION_MODEL", DEFAULT_SUMMARIZER),
        description="Model to use for verification (defaults to summarization model).",
    )
    verification_context_length: int = Field(
        default=50000,
        ge=1000,
        description="Maximum length of context used for verification to avoid token limits.",
    )

    # Strategy Configuration
    strategy_mapping: dict[DIKWLevel, str] = Field(
        default_factory=lambda: {
            DIKWLevel(k): v for k, v in DEFAULT_STRATEGY_MAPPING.items()
        },
        description="Mapping of DIKW levels to strategy names.",
    )
    dikw_topology: dict[str, DIKWLevel] = Field(
        default_factory=lambda: {
            "root": DIKWLevel.WISDOM,
            "intermediate": DIKWLevel.KNOWLEDGE,
            "leaf": DIKWLevel.INFORMATION,
        },
        description="Mapping of tree topology positions ('root', 'intermediate', 'leaf') to DIKW levels.",
    )

    @field_validator("embedding_model", mode="after")
    @classmethod
    def validate_embedding_model(cls, v: str) -> str:
        """Validate embedding model name to prevent potential issues."""
        if not v or not v.strip():
            msg = "Embedding model name cannot be empty."
            raise ValueError(msg)
        return _validate_model_name(v, ALLOWED_EMBEDDING_MODELS, "Embedding model")

    @field_validator("summarization_model", "verification_model", mode="after")
    @classmethod
    def validate_llm_model(cls, v: str) -> str:
        """Validate LLM model name against whitelist."""
        return _validate_model_name(v, ALLOWED_SUMMARIZATION_MODELS, "LLM model")

    @field_validator("tokenizer_model", mode="after")
    @classmethod
    def validate_tokenizer_model(cls, v: str) -> str:
        """Validate tokenizer model against whitelist."""
        return _validate_model_name(v, ALLOWED_TOKENIZER_MODELS, "Tokenizer model")

    @model_validator(mode="after")
    def validate_chunking_consistency(self) -> Self:
        """Ensure chunking parameters are consistent."""
        if self.semantic_chunking_mode and (
            self.semantic_chunking_threshold > 1.0 or self.semantic_chunking_threshold < 0.0
        ):
            msg = "Semantic chunking threshold must be between 0.0 and 1.0"
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
        return cls(max_tokens=HIGH_PRECISION_MAX_TOKENS, overlap=HIGH_PRECISION_OVERLAP)
