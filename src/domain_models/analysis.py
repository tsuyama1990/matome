from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class PivotAxis(StrEnum):
    ACTOR_STATE = "Actor vs. State Transition"
    OPPORTUNITIES_THREATS = "Opportunities vs Threats"
    TIME = "Time Axis"
    SWOT = "SWOT Analysis"
    PESTLE = "PESTLE Analysis"
    CUSTOM = "Custom Axis"

class PivotBoardNode(BaseModel):
    model_config = ConfigDict(extra="forbid")

    node_id: str = Field(..., description="Reference to the original DocumentNode ID")
    x_position: float = Field(..., description="Calculated X coordinate on the pivot board", ge=0.0, le=1.0)
    y_position: float = Field(..., description="Calculated Y coordinate on the pivot board", ge=0.0, le=1.0)
    cluster_id: str | None = Field(None, description="The cluster this node belongs to on the pivot board")

class PivotBoard(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(..., description="Unique identifier for the pivot board")
    original_root_id: str = Field(..., description="The root DocumentNode ID this board is based on")
    axis: PivotAxis = Field(..., description="The multidimensional axis used for this pivot")
    custom_axis_description: str | None = Field(None, description="Description if axis is CUSTOM")
    nodes: list[PivotBoardNode] = Field(default_factory=list, description="List of nodes positioned on this board")
    mermaid_diagram: str | None = Field(None, description="Generated Mermaid.js snippet for this board")
