from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class IdentityNode(BaseModel):
    """
    Represents the identity, topological position, and metadata of a node
    within the RAPTOR knowledge tree.
    """

    model_config = ConfigDict(extra="forbid")

    id: str = Field(..., description="Unique identifier for the node.")
    parent_id: str | None = Field(default=None, description="Identifier of the parent node.")
    children_ids: list[str] = Field(
        default_factory=list, description="Identifiers of children nodes."
    )
    level: int = Field(..., ge=0, description="Depth level in the hierarchy (0 is root).")
    is_locked: bool = Field(default=True, description="Whether the node is locked for reading.")
    tags: dict[str, Any] = Field(
        default_factory=dict, description="Multi-dimensional metadata tags."
    )


class ContentNode(BaseModel):
    """
    Represents the actual semantic content and summary associated with an IdentityNode.
    """

    model_config = ConfigDict(extra="forbid")

    id: str = Field(..., description="Matches the IdentityNode ID.")
    original_text: str = Field(..., description="The original chunk text from the document.")
    summary_text: str | None = Field(default=None, description="The Chain of Density summary text.")
    entities: list[str] = Field(
        default_factory=list, description="Named entities extracted from the text."
    )
