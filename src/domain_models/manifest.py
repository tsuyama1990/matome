import logging

from pydantic import BaseModel, ConfigDict, Field, model_validator

from domain_models.types import DIKWLevel, Metadata, NodeID

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
        # We strip to check, but we don't modify the actual text field here as it might be intentional?
        # No, RAPTOR chunks should contain meaningful content.
        if not self.text or not self.text.strip():
            msg = "Chunk text cannot be empty or whitespace only."
            logger.error(msg)
            raise ValueError(msg)

        # Simplified validation as requested by feedback
        # Empty text is already rejected above, so we can be strict about range
        if self.start_char_idx > self.end_char_idx:
            msg = (
                f"Invalid character range: start ({self.start_char_idx}) cannot be greater than "
                f"end ({self.end_char_idx})."
            )
            logger.error(msg)
            raise ValueError(msg)

        # Embedding Validation
        # Explicit check for None is implied by logic: if self.embedding is not None, we validate it.
        # If the schema allows None, we accept None.
        # However, if it's NOT None, we strictly validate content.
        if self.embedding is not None:
            if not isinstance(self.embedding, list):
                msg = "Embedding must be a list."
                raise ValueError(msg)
            if len(self.embedding) == 0:
                msg = "Embedding cannot be an empty list if provided."
                logger.error(msg)
                raise ValueError(msg)
            # Strictly enforce float values (no ints)
            if any(not isinstance(x, float) for x in self.embedding):
                msg = "Embedding must contain only float values."
                logger.error(msg)
                raise ValueError(msg)

        return self


class NodeMetadata(BaseModel):
    """
    Standardized metadata for SummaryNodes.
    """

    model_config = ConfigDict(extra="forbid")

    dikw_level: DIKWLevel = Field(
        default=DIKWLevel.DATA, description="The abstraction level of this node."
    )
    is_user_edited: bool = Field(
        default=False, description="True if the node content was refined by a user."
    )
    refinement_history: list[str] = Field(
        default_factory=list, description="Audit trail of refinement instructions."
    )
    cluster_id: int | str | None = Field(
        default=None, description="The ID of the cluster this node summarizes."
    )
    type: str | None = Field(default=None, description="Type of the node (e.g., 'single_chunk_root').")


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
        default_factory=NodeMetadata, description="Optional extra info (e.g., cluster ID)."
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


class DocumentTree(BaseModel):
    """
    Represents the full RAPTOR tree structure.

    Designed for scalability:
    - Does not store full leaf chunks in memory to avoid O(N) memory usage for large documents.
    - Stores IDs allowing retrieval from the associated `DiskChunkStore`.
    """

    model_config = ConfigDict(extra="forbid")

    root_node: SummaryNode = Field(..., description="The root summary node.")
    all_nodes: dict[str, SummaryNode] = Field(..., description="Map of all summary nodes by ID.")
    leaf_chunk_ids: list[NodeID] = Field(
        ..., description="IDs of the original leaf chunks (Level 0)."
    )
    metadata: Metadata = Field(default_factory=dict, description="Global metadata for the tree.")
