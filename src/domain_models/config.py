from typing import Self

from pydantic import BaseModel, ConfigDict, Field


class ChunkingConfig(BaseModel):
    """Configuration for text chunking."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    max_tokens: int = Field(default=500, ge=1, description="Maximum number of tokens per chunk.")
    overlap: int = Field(
        default=0, ge=0, description="Number of overlapping tokens between chunks."
    )
    tokenizer_model: str = Field(
        default="cl100k_base", description="Tokenizer model/encoding name to use."
    )


class EmbeddingConfig(BaseModel):
    """Configuration for embedding generation."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    model_name: str = Field(
        default="intfloat/multilingual-e5-large", description="HuggingFace model name for embeddings."
    )
    batch_size: int = Field(
        default=32, ge=1, description="Batch size for embedding generation."
    )


class ClusteringConfig(BaseModel):
    """Configuration for clustering (UMAP + GMM)."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    algorithm: str = Field(
        default="gmm", description="Algorithm to use (e.g., 'gmm'). Currently only 'gmm' is supported."
    )
    n_clusters: int | None = Field(
        default=None, description="Fixed number of clusters (if applicable)."
    )
    random_state: int = Field(
        default=42, description="Random seed for reproducibility."
    )

    # UMAP Configuration
    umap_n_components: int = Field(
        default=5, ge=2, description="Number of dimensions for UMAP reduction."
    )
    umap_n_neighbors: int = Field(
        default=15, ge=2, description="Number of neighbors for UMAP."
    )
    umap_metric: str = Field(
        default="cosine", description="Distance metric for UMAP."
    )

    # GMM Configuration
    gmm_n_components_min: int = Field(
        default=2, ge=2, description="Minimum number of clusters for GMM BIC search."
    )
    gmm_n_components_max: int = Field(
        default=20, ge=2, description="Maximum number of clusters for GMM BIC search."
    )
    gmm_covariance_type: str = Field(
        default="full", description="Covariance type for GMM."
    )


class SummarizationConfig(BaseModel):
    """Configuration for summarization."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    model_name: str = Field(
        default="gpt-4o", description="Model to use for summarization."
    )
    max_summary_tokens: int = Field(
        default=200, ge=1, description="Target token count for summaries."
    )


class ProcessingConfig(BaseModel):
    """
    Main configuration aggregating all sub-configurations.
    This acts as the single source of truth for pipeline settings.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    chunking: ChunkingConfig = Field(default_factory=ChunkingConfig)
    embedding: EmbeddingConfig = Field(default_factory=EmbeddingConfig)
    clustering: ClusteringConfig = Field(default_factory=ClusteringConfig)
    summarization: SummarizationConfig = Field(default_factory=SummarizationConfig)

    @classmethod
    def default(cls) -> Self:
        """
        Returns the default configuration.
        """
        return cls()

    @classmethod
    def high_precision(cls) -> Self:
        """
        Returns a configuration optimized for higher precision (smaller chunks).
        """
        return cls(
            chunking=ChunkingConfig(max_tokens=200, overlap=20)
        )
