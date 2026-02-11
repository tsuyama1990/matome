from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class DIKWLevel(StrEnum):
    """
    The Semantic Zooming Level.
    Wisdom: L1 (Root) - Abstract, Philosophical.
    Knowledge: L2 (Branches) - Structural, Explanatory.
    Information: L3 (Twigs) - Actionable, Procedural.
    Data: L4 (Leaves) - Raw Evidence.
    """

    WISDOM = "wisdom"
    KNOWLEDGE = "knowledge"
    INFORMATION = "information"
    DATA = "data"


class NodeMetadata(BaseModel):
    """
    Standardized metadata for SummaryNodes.
    """

    model_config = ConfigDict(extra="allow")  # Allow extra fields for backward compatibility

    dikw_level: DIKWLevel | None = Field(
        default=None, description="The abstraction level of this node."
    )
    is_user_edited: bool = Field(
        default=False,
        description="True if the user has manually refined this node. Prevents auto-overwrite.",
    )
    prompt_history: list[str] = Field(
        default_factory=list, description="History of prompts used to generate/refine this node."
    )
    # Origin fields (existing use cases)
    cluster_id: int | str | None = None
    source_chunk_indices: list[int] | None = None
