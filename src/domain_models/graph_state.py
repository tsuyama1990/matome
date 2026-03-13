from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

from src.domain_models.document import EnrichedDocument


class ProcessingStatus(StrEnum):
    """The explicit states of the workflow orchestration."""

    INITIAL = "INITIAL"
    CHUNKING = "CHUNKING"
    EMBEDDING = "EMBEDDING"
    CLUSTERING = "CLUSTERING"
    SUMMARIZING = "SUMMARIZING"
    COMPLETE = "COMPLETE"
    FAILED = "FAILED"


class GraphState(BaseModel):
    """The state passed between LangGraph nodes during orchestration."""

    current_document: EnrichedDocument | None = Field(
        default=None, description="The document being processed."
    )
    source_filepath: str | None = Field(
        default=None, description="The original filepath of the uploaded document."
    )
    processing_status: ProcessingStatus = Field(
        default=ProcessingStatus.INITIAL, description="The current status of the workflow."
    )
    error_log: list[str] = Field(
        default_factory=list, description="A log of errors encountered during processing."
    )

    model_config = ConfigDict(extra="forbid")

    def transition_status(self, new_status: ProcessingStatus) -> None:
        """Transitions to a new state explicitly, ensuring valid transition paths."""
        valid_transitions = {
            ProcessingStatus.INITIAL: [ProcessingStatus.CHUNKING, ProcessingStatus.FAILED],
            ProcessingStatus.CHUNKING: [ProcessingStatus.EMBEDDING, ProcessingStatus.FAILED],
            ProcessingStatus.EMBEDDING: [ProcessingStatus.CLUSTERING, ProcessingStatus.FAILED],
            ProcessingStatus.CLUSTERING: [ProcessingStatus.SUMMARIZING, ProcessingStatus.FAILED],
            ProcessingStatus.SUMMARIZING: [ProcessingStatus.COMPLETE, ProcessingStatus.FAILED],
            ProcessingStatus.COMPLETE: [],
            ProcessingStatus.FAILED: [],
        }

        if new_status not in valid_transitions[self.processing_status]:
            msg = f"Invalid transition from {self.processing_status} to {new_status}"
            raise ValueError(msg)

        self.processing_status = new_status

    def add_error(self, error_message: str) -> None:
        """Adds an error to the error log, optionally failing the status automatically."""
        self.error_log.append(error_message)

    def set_document(self, document: EnrichedDocument) -> None:
        """Sets the document context into the current state machine flow."""
        self.current_document = document
