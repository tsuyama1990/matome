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

    node_id: str = Field(..., description="Reference to the original DocumentNode ID", max_length=100, pattern=r'^[a-zA-Z0-9_-]+$')
    x_position: float = Field(..., description="Calculated X coordinate on the pivot board", ge=0.0, le=1.0)
    y_position: float = Field(..., description="Calculated Y coordinate on the pivot board", ge=0.0, le=1.0)
    cluster_id: str | None = Field(None, description="The cluster this node belongs to on the pivot board", max_length=100, pattern=r'^[a-zA-Z0-9_-]+$')

class PivotBoard(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(..., description="Unique identifier for the pivot board", max_length=100, pattern=r'^[a-zA-Z0-9_-]+$')
    original_root_id: str = Field(..., description="The root DocumentNode ID this board is based on", max_length=100, pattern=r'^[a-zA-Z0-9_-]+$')
    axis: PivotAxis = Field(..., description="The multidimensional axis used for this pivot")
    custom_axis_description: str | None = Field(None, description="Description if axis is CUSTOM", max_length=500)
    nodes: list[PivotBoardNode] = Field(default_factory=list, description="List of nodes positioned on this board")

class PivotBoardView(BaseModel):
    model_config = ConfigDict(extra="forbid")

    board_id: str = Field(..., description="The ID of the PivotBoard this view renders", max_length=100)
    mermaid_diagram: str = Field(..., description="Generated Mermaid.js snippet for this board", max_length=50000)
