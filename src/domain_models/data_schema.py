from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class DIKWLevel(StrEnum):
    """
    DIKW (Data, Information, Knowledge, Wisdom) Hierarchy Levels.
    """
    WISDOM = "wisdom"       # L1: Philosophical/Abstract
    KNOWLEDGE = "knowledge" # L2: Frameworks/Mechanisms
    INFORMATION = "information" # L3: Actionable/How-to
    DATA = "data"           # L0/L4: Raw Chunks/Evidence


class NodeMetadata(BaseModel):
    """
    Standardized metadata schema for SummaryNodes.
    Allows extra fields for backward compatibility with legacy dict metadata.
    """
    model_config = ConfigDict(extra="allow")

    dikw_level: DIKWLevel = Field(..., description="The DIKW level of the node.")
    is_user_edited: bool = Field(default=False, description="Whether the node content was manually edited by a user.")
    refinement_history: list[str] = Field(default_factory=list, description="History of refinement instructions applied to this node.")

    # Optional fields that might be present in legacy data or needed for clustering
    cluster_id: int | str | None = Field(default=None, description="ID of the cluster this node belongs to.")
    type: str | None = Field(default=None, description="Type of the node (e.g., 'single_chunk_root').")
