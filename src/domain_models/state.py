from pydantic import BaseModel, ConfigDict, Field

from src.domain_models.chunk import SemanticChunk
from src.domain_models.graph import SummaryTree
from src.domain_models.pivot import PivotResponse


class GraphState(BaseModel):
    """The strictly typed State object passed between LangGraph nodes."""

    model_config = ConfigDict(extra="forbid")

    file_path: str | None = None
    raw_text: str | None = None
    cleaned_text: str | None = None
    chunks: list[SemanticChunk] = Field(default_factory=list)
    embedded_chunks: bool = False
    tree: SummaryTree | None = None
    active_node_id: str | None = None
    pivot_axis: str | None = None
    pivot_response: PivotResponse | None = None
    error: str | None = None
