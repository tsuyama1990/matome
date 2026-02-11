from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class DIKWLevel(StrEnum):
    """Abstraction levels in the DIKW hierarchy."""

    WISDOM = "wisdom"
    KNOWLEDGE = "knowledge"
    INFORMATION = "information"
    DATA = "data"


class NodeMetadata(BaseModel):
    """
    Metadata associated with a SummaryNode, enforcing the DIKW schema
    while allowing extra fields for backward compatibility.
    """

    model_config = ConfigDict(extra="allow")

    dikw_level: DIKWLevel = Field(
        default=DIKWLevel.DATA, description="The abstraction level of this node."
    )
    is_user_edited: bool = Field(
        default=False, description="True if the user has manually refined this node."
    )
    refinement_history: list[str] = Field(
        default_factory=list, description="List of user instructions applied to this node."
    )
