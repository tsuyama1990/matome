from pydantic import BaseModel, ConfigDict, Field

from src.domain_models.chunk import SemanticChunk
from src.domain_models.graph import SummaryTree
from src.domain_models.pivot import PivotResponse


class GraphState(BaseModel):
    """The strictly typed State object passed between LangGraph nodes."""

    model_config = ConfigDict(extra="forbid")

    file_path: str | None = None
    chunks: list[SemanticChunk] = Field(default_factory=list)
    tree: SummaryTree | None = None
    active_node_id: str | None = None
    pivot_axis: str | None = None
    pivot_response: PivotResponse | None = None
    error: str | None = None

    # Internal variables for RAPTOR state management within LangGraph
    embeddings: list[list[float]] | None = None
    reduced_embeddings: list[list[float]] | None = None
    cluster_assignments: list[int] | None = None
