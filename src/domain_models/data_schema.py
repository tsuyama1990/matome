from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

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

    # Enforce strict schema validation ("forbid").
    # We use a validator to strip extra fields from legacy data BEFORE validation,
    # satisfying both strictness (for new code) and backward compatibility (for old data).
    model_config = ConfigDict(extra="forbid")

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

    @model_validator(mode="before")
    @classmethod
    def strip_extra_fields(cls, data: Any) -> Any:
        """
        Strip unknown fields from the input dictionary before validation.
        This allows legacy data with extra fields to be loaded without error,
        while maintaining strict schema enforcement on the resulting model.
        """
        if isinstance(data, dict):
            # Identify fields defined in the model
            allowed_fields = set(cls.model_fields.keys())
            # Return a new dict with only allowed fields
            return {k: v for k, v in data.items() if k in allowed_fields}
        return data
