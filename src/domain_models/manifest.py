from typing import Any, TypeAlias

from pydantic import BaseModel, ConfigDict, Field, model_validator

# Define a type alias for Metadata to improve readability and consistency.
# Metadata is a flexible dictionary used to store arbitrary context (e.g., source file path,
# timestamps, author info, or processing metrics) that doesn't fit into the core schema.
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

        Strictly, if text is non-empty, start < end.
        If text is empty (unlikely but possible), start == end.
        But generally chunks should have content.

        Let's enforce start <= end generally, and maybe warn or fail on empty content?
        The feedback requested: "Disallow zero-length chunks".
        So: start < end AND text not empty.
        """
        if self.start_char_idx > self.end_char_idx:
            msg = (
                f"start_char_idx ({self.start_char_idx}) cannot be greater than "
                f"end_char_idx ({self.end_char_idx})"
            )
            raise ValueError(msg)

        # Check for zero length if strictly required
        if self.start_char_idx == self.end_char_idx and self.text:
            # If text has content but indices are same -> error
             msg = f"Zero-length range ({self.start_char_idx}-{self.end_char_idx}) but text is not empty."
             raise ValueError(msg)

        if not self.text and self.start_char_idx != self.end_char_idx:
             # If text is empty but range is not -> error
             msg = f"Empty text but range is not zero-length ({self.start_char_idx}-{self.end_char_idx})."
             raise ValueError(msg)

        # Disallow empty chunks entirely?
        if not self.text:
            msg = "Chunk text cannot be empty."
            raise ValueError(msg)

        return self


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
    """Represents a cluster of nodes identified for summarization."""

    model_config = ConfigDict(extra="forbid")

    id: int | str = Field(..., description="Cluster identifier.")
    level: int = Field(..., ge=0, description="Level of the nodes in this cluster.")
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
