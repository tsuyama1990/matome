from typing import Any

from pydantic import BaseModel, ConfigDict


class PivotResponse(BaseModel):
    """The response containing the restructured knowledge based on a pivot axis."""

    model_config = ConfigDict(extra="forbid")

    axis: str
    restructured_nodes: list[dict[str, Any]]
    mermaid_diagram: str
