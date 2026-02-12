from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

from domain_models.constants import DEFAULT_DIKW_LEVEL
from domain_models.types import NodeID


class DIKWLevel(StrEnum):
    """
    The abstraction level of a summary node in the DIKW hierarchy.
    """

    WISDOM = "wisdom"
    KNOWLEDGE = "knowledge"
    INFORMATION = "information"
    DATA = "data"


class NodeMetadata(BaseModel):
    """
    Metadata associated with a SummaryNode.
    Acts as the single source of truth for a node's semantic properties.
    """

    # Use extra="ignore" to support backward compatibility with legacy data.
    # This prevents crashes when loading old databases with deprecated fields,
    # satisfying the requirement "Existing databases must load correctly".
    model_config = ConfigDict(extra="ignore")

    # Existing fields (explicitly typed for better IDE support)
    cluster_id: NodeID | None = Field(
        default=None, description="The ID of the cluster this node summarizes."
    )
    type: str | None = Field(
        default=None, description="The type of the node (e.g., 'summary', 'chunk')."
    )

    # New fields for Cycle 01
    dikw_level: DIKWLevel = Field(
        default=DIKWLevel(DEFAULT_DIKW_LEVEL),
        description="The abstraction level of this node.",
    )
    is_user_edited: bool = Field(
        default=False, description="True if the content has been manually refined by a user."
    )
    refinement_history: list[str] = Field(
        default_factory=list,
        description="History of refinement instructions applied to this node.",
        min_length=0,
    )
