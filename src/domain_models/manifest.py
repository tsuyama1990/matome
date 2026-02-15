from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from domain_models.types import DIKWLevel, Metadata, NodeID


class Document(BaseModel):
    """Represents the raw input file."""

    model_config = ConfigDict(extra="forbid")

    content: str = Field(..., description="Full text content of the document.")
    metadata: Metadata = Field(
        default_factory=dict, description="Metadata associated with the document (e.g., filename)."
    )


class NodeMetadata(BaseModel):
    """
    Metadata for a summary node.
    Enforces strict schema validation.
    """
    model_config = ConfigDict(extra="forbid", frozen=False)

    dikw_level: DIKWLevel = Field(
        default=DIKWLevel.DATA, description="The DIKW level of the node."
    )
    is_user_edited: bool = Field(
        default=False, description="Whether the node has been manually edited."
    )
    refinement_history: list[str] = Field(
        default_factory=list, description="History of refinement instructions applied."
    )
    cluster_id: int | None = Field(
        default=None, description="ID of the cluster this node summarizes."
    )
    type: str | None = Field(
        default=None, description="Type identifier for the node (e.g., 'single_chunk_root')."
    )


class Chunk(BaseModel):
    """
    Represents a chunk of text from the source document.
    """
    model_config = ConfigDict(extra="forbid")

    index: int = Field(..., ge=0, description="Sequential index of the chunk.")
    text: str = Field(..., min_length=1, description="Text content of the chunk.")
    start_char_idx: int = Field(..., ge=0, description="Start character index.")
    end_char_idx: int = Field(..., ge=0, description="End character index.")
    embedding: list[float] | None = None
    metadata: Metadata = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_indices(self) -> "Chunk":
        if self.start_char_idx > self.end_char_idx:
            raise ValueError("start_char_idx cannot be greater than end_char_idx")
        return self

    @model_validator(mode="after")
    def validate_embedding(self) -> "Chunk":
        if self.embedding is not None and len(self.embedding) == 0:
            raise ValueError("Embedding cannot be empty list")
        return self


class SummaryNode(BaseModel):
    """
    Represents a summarized node in the tree.
    """
    model_config = ConfigDict(extra="forbid")

    id: NodeID
    text: str
    level: int = Field(..., ge=1, description="Level in the tree (1+).")
    children_indices: list[NodeID]
    metadata: NodeMetadata
    embedding: list[float] | None = None


class Cluster(BaseModel):
    """
    Represents a cluster of nodes.
    """
    model_config = ConfigDict(extra="forbid")

    id: int
    level: int = Field(..., ge=0, description="Level of the cluster.")
    node_indices: list[NodeID]
    metadata: dict[str, Any] = Field(default_factory=dict)
    centroid: list[float] | None = Field(default=None)


class DocumentTree(BaseModel):
    """
    Represents the full hierarchical tree structure.
    """
    model_config = ConfigDict(extra="forbid")

    root_node: SummaryNode | Chunk | None = None
    leaf_chunk_ids: list[NodeID] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
