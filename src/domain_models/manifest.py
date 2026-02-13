import logging
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from domain_models.data_schema import NodeMetadata
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

    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    index: int = Field(..., ge=0, description="Sequential ID of the chunk.")
    text: str = Field(..., min_length=1, description="The actual text content of the chunk.")
    start_char_idx: int = Field(
        ..., ge=0, description="Starting character position in the original text."
    )
    end_char_idx: int = Field(
        ..., ge=0, description="Ending character position in the original text."
    )
    # Embedding is optional during initial chunking, but required for clustering/persistence.
    embedding: list[float] | None = Field(
        default=None, description="The vector representation of the chunk text."
    )
    metadata: Metadata = Field(
        default_factory=dict, description="Optional extra info about the chunk."
    )

    @model_validator(mode="after")
    def check_indices(self) -> "Chunk":
        """
        Validate that text is present and indices form a valid range.
        Also check embedding validity if present.
        """
        # Ensure text is not just whitespace and not empty
        if not self.text or not self.text.strip():
            msg = "Chunk text cannot be empty or whitespace only."
            logger.error(msg)
            raise ValueError(msg)

        if self.start_char_idx > self.end_char_idx:
            msg = (
                f"Invalid character range: start ({self.start_char_idx}) cannot be greater than "
                f"end ({self.end_char_idx})."
            )
            logger.error(msg)
            raise ValueError(msg)

        if self.embedding is not None:
            if len(self.embedding) == 0:
                msg = "Embedding cannot be an empty list if provided."
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
    embedding: list[float] | None = Field(
        default=None, description="The vector representation of the summary text."
    )
    metadata: NodeMetadata = Field(
        ..., description="Metadata including DIKW level and refinement history."
    )

    @model_validator(mode="before")
    @classmethod
    def parse_metadata(cls, data: Any) -> Any:
        """
        Allow initialization with a dict for metadata by parsing it into NodeMetadata.
        This supports loading from legacy JSON storage or dict-based tests.
        """
        if isinstance(data, dict):
            meta = data.get("metadata")
            if isinstance(meta, dict):
                # If we are loading from a dict that doesn't have 'dikw_level',
                # we might need to handle it or let Pydantic validation handle it.
                pass
        return data


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


class DocumentTree(BaseModel):
    """
    Represents the full RAPTOR tree structure.
    """

    model_config = ConfigDict(extra="forbid")

    root_node: SummaryNode = Field(..., description="The root summary node.")
    leaf_chunk_ids: list[NodeID] = Field(
        ..., description="IDs of the original leaf chunks (Level 0)."
    )
    metadata: Metadata = Field(default_factory=dict, description="Global metadata for the tree.")
    all_nodes: None = None
