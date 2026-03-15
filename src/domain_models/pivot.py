import re
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator
from pydantic_core.core_schema import ValidationInfo


class PivotNode(BaseModel):
    """
    A node representing a concept on a new axis in the reconstructed graph.
    """

    node_id: str = Field(description="Unique identifier for the node.")
    label: str = Field(description="The label or name of this category/concept.")
    summary: str = Field(description="A descriptive summary of what this node represents.")
    source_chunk_ids: list[UUID] = Field(
        min_length=1,
        description="List of original SemanticChunk UUIDs providing evidence for this node.",
    )

    model_config = ConfigDict(extra="forbid")


class PivotState(BaseModel):
    """
    The overall state of the newly formed graph based on a specific axis.
    """

    original_document_id: UUID = Field(description="The ID of the document this pivot is based on.")
    axis_name: str = Field(description="The name of the multi-dimensional axis used (e.g., SWOT).")
    nodes: list[PivotNode] = Field(description="List of nodes constructed for this axis.")

    model_config = ConfigDict(extra="forbid")


class PivotResponse(BaseModel):
    """
    Response model for Pivot Workflow.
    """

    markdown: str = Field(description="Generated markdown string.")
    mermaid: str = Field(description="Generated mermaid string.")
    clusters: dict[str, list[dict[str, str]]] = Field(description="Serialized clusters mappings.")

    model_config = ConfigDict(extra="forbid")


class PivotRequestPayload(BaseModel):
    """
    Payload for requesting a pivot KJ analysis.
    Supported axes: 'actor', 'time', 'entities'.
    """

    axis: str = Field(
        ...,
        min_length=1,
        max_length=50,
        description="The multi-dimensional axis to pivot on (e.g., actor, time, entities).",
    )

    @field_validator("axis")
    @classmethod
    def validate_axis_format(cls, v: str, info: ValidationInfo) -> str:
        """Validates that the axis string is alphanumeric and safe from injection."""
        _ = info
        v = v.strip().lower()
        if not re.match(r"^[a-zA-Z0-9\s_-]+$", v):
            msg = "Axis must contain only alphanumeric characters, spaces, dashes, or underscores."
            raise ValueError(msg)
        return v

    model_config = ConfigDict(extra="forbid")
