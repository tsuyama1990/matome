from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, field_validator


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

    @field_validator("refinement_history")
    @classmethod
    def validate_refinement_history(cls, v: list[str]) -> list[str]:
        """Validate refinement history content and size."""
        MAX_HISTORY_SIZE = 50
        if len(v) > MAX_HISTORY_SIZE:
            # We truncate from the beginning (keeping latest) or raise error?
            # Keeping strictly valid, we raise or truncate.
            # Usually truncation is safer for history logs.
            # But "Data Integrity" suggests strictness.
            # Let's keep the last N entries.
            return v[-MAX_HISTORY_SIZE:]

        # Validate content type is string (Pydantic does this, but we can check constraints)
        for entry in v:
            if not isinstance(entry, str):
                msg = "Refinement history entries must be strings."
                raise TypeError(msg)
            if len(entry) > 10000: # Arbitrary large limit to prevent DoS
                msg = "Refinement history entry too long."
                raise ValueError(msg)
        return v
