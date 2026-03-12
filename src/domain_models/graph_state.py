from pydantic import BaseModel, ConfigDict, Field

from src.domain_models.document import EnrichedDocument


class GraphState(BaseModel):
    """The state passed between LangGraph nodes during orchestration."""

    current_document: EnrichedDocument | None = Field(
        default=None, description="The document being processed."
    )
    processing_status: str = Field(
        default="initial", description="The current status of the workflow."
    )
    error_log: list[str] = Field(
        default_factory=list, description="A log of errors encountered during processing."
    )

    model_config = ConfigDict(extra="forbid")
