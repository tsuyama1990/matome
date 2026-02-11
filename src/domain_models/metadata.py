from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator


class DIKWLevel(StrEnum):
    """
    Defines the four levels of the DIKW hierarchy.
    """
    WISDOM = "wisdom"
    KNOWLEDGE = "knowledge"
    INFORMATION = "information"
    DATA = "data"


class NodeMetadata(BaseModel):
    """
    Metadata schema for SummaryNodes, supporting the DIKW hierarchy.
    Allows extra fields for backward compatibility.
    """

    dikw_level: DIKWLevel = Field(
        default=DIKWLevel.DATA,
        description="The abstraction level of this node."
    )
    is_user_edited: bool = Field(
        default=False,
        description="True if the user has manually refined this node."
    )
    refinement_history: list[str] = Field(
        default_factory=list,
        description="List of user instructions applied to this node."
    )

    # Allow extra fields for backward compatibility with existing unstructured metadata
    model_config = ConfigDict(extra="allow")

    @model_validator(mode="before")
    @classmethod
    def validate_legacy_dict(cls, data: Any) -> Any:
        """
        Ensures input data is compatible.
        If it's a dict, we let Pydantic handle field mapping and extra fields.
        """
        return data
