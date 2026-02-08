import logging
from typing import Any, TypeAlias

from pydantic import BaseModel, ConfigDict, Field, model_validator

# Configure logger
logger = logging.getLogger(__name__)

# Define a type alias for Metadata to improve readability and consistency.
Metadata: TypeAlias = dict[str, Any]


class Document(BaseModel):
    """Represents the raw input file."""

    model_config = ConfigDict(extra="forbid")

    content: str = Field(..., description="Full text content of the document.")
    metadata: Metadata = Field(
        default_factory=dict, description="Metadata associated with the document (e.g., filename)."
    )


class Chunk(BaseModel):
    """Represents a segment of text (Leaf Node in RAPTOR tree)."""

    model_config = ConfigDict(extra="forbid")

    index: int = Field(..., ge=0, description="Sequential ID of the chunk.")
    text: str = Field(..., description="The actual text content of the chunk.")
    start_char_idx: int = Field(
        ..., ge=0, description="Starting character position in the (processed) text."
    )
    end_char_idx: int = Field(
        ..., ge=0, description="Ending character position in the (processed) text."
    )
    embedding: list[float] | None = Field(
        default=None, description="The vector representation of the chunk text."
    )
    metadata: Metadata = Field(
        default_factory=dict, description="Optional extra info about the chunk."
    )

    @model_validator(mode="after")
    def check_integrity(self) -> "Chunk":
        """
        Validate chunk integrity.
        Ensures text is not empty and indices align with text length.
        Also validates embedding integrity if present.
        """
        if not self.text:
            msg = "Chunk text cannot be empty."
            logger.error(msg)
            raise ValueError(msg)

        if not self.text.strip():
            msg = "Chunk text cannot be just whitespace (post-normalization check)."
            logger.error(msg)
            raise ValueError(msg)

        if self.start_char_idx >= self.end_char_idx:
            msg = (
                f"Invalid indices: start_char_idx ({self.start_char_idx}) must be less than "
                f"end_char_idx ({self.end_char_idx}) for non-empty text."
            )
            logger.error(msg)
            raise ValueError(msg)

        # We relax the strict length check because normalization (NFKC) can change length
        # (e.g., full-width to half-width).
        # We only check that if indices claim non-empty, text is not empty (already checked above).

        # Verify that text is not empty after potential normalization/strip
        if not self.text.strip():
            msg = "Chunk text cannot be empty or just whitespace."
            logger.error(msg)
            raise ValueError(msg)

        if self.embedding is not None and len(self.embedding) == 0:
            msg = "Embedding vector cannot be empty if provided."
            logger.error(msg)
            raise ValueError(msg)

        return self

    def require_embedding(self) -> list[float]:
        """
        Returns the embedding if present, otherwise raises ValueError.
        Use this when processing requires embeddings.
        """
        if self.embedding is None:
            msg = f"Chunk {self.index} requires an embedding but none is set."
            logger.error(msg)
            raise ValueError(msg)
        return self.embedding


class SummaryNode(BaseModel):
    """Represents a summary node in the RAPTOR tree."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(..., description="Unique identifier for the node.")
    text: str = Field(..., description="The summary text.")
    level: int = Field(..., ge=1, description="Hierarchical level (1 = above chunks).")
    children_indices: list[int | str] = Field(
        ..., description="List of child indices (Chunk index or SummaryNode ID)."
    )
    metadata: Metadata = Field(
        default_factory=dict, description="Optional extra info (e.g., cluster ID)."
    )


class Cluster(BaseModel):
    """
    Represents a cluster of nodes identified for summarization.

    A cluster groups nodes (Chunks or SummaryNodes) that are semantically similar.
    """

    model_config = ConfigDict(extra="forbid")

    id: str = Field(..., description="Cluster identifier.")
    level: int = Field(..., ge=0, description="Level of the nodes in this cluster (0 for chunks).")
    node_indices: list[int | str] = Field(
        ..., description="Indices of nodes (Chunks or SummaryNodes) in this cluster."
    )
    centroid: list[float] | None = Field(
        default=None, description="Vector centroid of the cluster (optional)."
    )


class Tree(BaseModel):
    """Represents the full RAPTOR tree structure."""

    model_config = ConfigDict(extra="forbid")

    chunks: list[Chunk] = Field(..., description="Original text chunks (Level 0).")
    summaries: list[SummaryNode] = Field(..., description="Generated summary nodes (Level 1+).")
    metadata: Metadata = Field(default_factory=dict, description="Global metadata for the tree.")
