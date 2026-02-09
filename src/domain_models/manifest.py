import logging

from pydantic import BaseModel, ConfigDict, Field, model_validator

from domain_models.types import Metadata, NodeID

# Configure logger
logger = logging.getLogger(__name__)


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
        ..., ge=0, description="Starting character position in the original text."
    )
    end_char_idx: int = Field(
        ..., ge=0, description="Ending character position in the original text."
    )
    embedding: list[float] | None = Field(
        default=None, description="The vector representation of the chunk text."
    )
    metadata: Metadata = Field(
        default_factory=dict, description="Optional extra info about the chunk."
    )

    @model_validator(mode="after")
    def check_indices(self) -> "Chunk":
        """
        Validate that start_char_idx is less than or equal to end_char_idx.
        Also check embedding validity if present.
        """
        # Index Validation
        if self.start_char_idx > self.end_char_idx:
            msg = (
                f"start_char_idx ({self.start_char_idx}) cannot be greater than "
                f"end_char_idx ({self.end_char_idx})"
            )
            logger.error(msg)
            raise ValueError(msg)

        if self.start_char_idx == self.end_char_idx and self.text:
             msg = f"Zero-length range ({self.start_char_idx}-{self.end_char_idx}) but text is not empty."
             logger.error(msg)
             raise ValueError(msg)

        if not self.text and self.start_char_idx != self.end_char_idx:
             msg = f"Empty text but range is not zero-length ({self.start_char_idx}-{self.end_char_idx})."
             logger.error(msg)
             raise ValueError(msg)

        if not self.text:
            msg = "Chunk text cannot be empty."
            logger.error(msg)
            raise ValueError(msg)

        # Embedding Validation
        if self.embedding is not None:
            if not self.embedding:
                msg = "Embedding cannot be an empty list."
                logger.error(msg)
                raise ValueError(msg)
            if any(not isinstance(x, (float, int)) for x in self.embedding):
                 msg = "Embedding must contain only numeric values."
                 logger.error(msg)
                 raise ValueError(msg)

        return self


class SummaryNode(BaseModel):
    """Represents a summary node in the RAPTOR tree."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(..., description="Unique identifier for the node.")
    text: str = Field(..., description="The summary text.")
    level: int = Field(..., ge=1, description="Hierarchical level (1 = above chunks).")
    children_indices: list[NodeID] = Field(
        ..., description="List of child indices (Chunk index or SummaryNode ID)."
    )
    metadata: Metadata = Field(
        default_factory=dict, description="Optional extra info (e.g., cluster ID)."
    )


class Cluster(BaseModel):
    """Represents a cluster of nodes identified for summarization."""

    model_config = ConfigDict(extra="forbid")

    id: NodeID = Field(..., description="Cluster identifier.")
    level: int = Field(..., ge=0, description="Level of the nodes in this cluster.")
    node_indices: list[NodeID] = Field(
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
