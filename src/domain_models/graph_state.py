from datetime import datetime
from enum import StrEnum
from typing import ClassVar
from uuid import UUID

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


class StateTransitionConfig:
    """Decouples valid state transitions into an independent configuration."""

    # A mapping of allowed transitions from a given state
    VALID_TRANSITIONS: ClassVar[dict[ProcessingStatus, list[ProcessingStatus]]] = {
        ProcessingStatus.INITIAL: [ProcessingStatus.CHUNKING, ProcessingStatus.FAILED],
        ProcessingStatus.CHUNKING: [ProcessingStatus.EMBEDDING, ProcessingStatus.FAILED],
        ProcessingStatus.EMBEDDING: [ProcessingStatus.CLUSTERING, ProcessingStatus.FAILED],
        ProcessingStatus.CLUSTERING: [ProcessingStatus.SUMMARIZING, ProcessingStatus.FAILED],
        ProcessingStatus.SUMMARIZING: [ProcessingStatus.COMPLETE, ProcessingStatus.FAILED],
        ProcessingStatus.COMPLETE: [],
        ProcessingStatus.FAILED: [],
    }

    @classmethod
    def validate_transition(cls, current: ProcessingStatus, target: ProcessingStatus) -> None:
        """Validates if a target state is accessible from the current state."""
        allowed = cls.VALID_TRANSITIONS.get(current, [])
        if target not in allowed:
            msg = f"Invalid transition from {current} to {target}"
            raise ValueError(msg)


class UnlockAttempt(BaseModel):
    """A single attempt by a user to unlock a node."""

    node_id: str = Field(description="The ID of the node attempted.")
    user_answer: str = Field(description="The answer provided by the user.")
    is_correct: bool = Field(description="Whether the answer was correct.")
    timestamp: datetime = Field(description="When the attempt was made.")

    model_config = ConfigDict(extra="forbid")


class LearningProgress(BaseModel):
    """Tracks a user's overall progress on a specific document."""

    document_id: UUID = Field(description="The document being learned.")
    unlocked_node_ids: set[str] = Field(
        default_factory=set, description="Set of unlocked node IDs."
    )
    history: list[UnlockAttempt] = Field(
        default_factory=list, description="History of unlock attempts."
    )

    model_config = ConfigDict(extra="forbid")


class GraphState(BaseModel):
    """The state passed between LangGraph nodes during orchestration."""

    current_document: EnrichedDocument | None = Field(
        default=None, description="The document being processed."
    )
    processing_status: ProcessingStatus = Field(
        default=ProcessingStatus.INITIAL, description="The current status of the workflow."
    )
    error_log: list[str] = Field(
        default_factory=list, description="A log of errors encountered during processing."
    )
    clustering_metadata: dict[str, str] = Field(
        default_factory=dict, description="Metadata generated during clustering and summarization."
    )

    model_config = ConfigDict(extra="forbid")

    def transition_status(self, new_status: ProcessingStatus) -> None:
        """Transitions to a new state explicitly, delegating to StateTransitionConfig."""
        StateTransitionConfig.validate_transition(self.processing_status, new_status)
        self.processing_status = new_status

    def add_error(self, error_message: str) -> None:
        """Adds an error to the error log, optionally failing the status automatically."""
        self.error_log.append(error_message)

    def set_document(self, document: EnrichedDocument) -> None:
        """Sets the document context into the current state machine flow."""
        self.current_document = document
