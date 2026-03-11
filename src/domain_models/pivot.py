from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class RestructuredNode(BaseModel):
    """A node that has been relocated or transformed within a PivotResponse."""

    model_config = ConfigDict(extra="forbid")

    id: str
    original_id: str | None = None
    title: str
    position_data: dict[str, Any] = Field(default_factory=dict)


class PivotResponse(BaseModel):
    """The response containing the restructured knowledge based on a pivot axis."""

    model_config = ConfigDict(extra="forbid")

    axis: str
    restructured_nodes: list[RestructuredNode] = Field(default_factory=list)
    mermaid_diagram: str
