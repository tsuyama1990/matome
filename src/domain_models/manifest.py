from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class NodeStatus(StrEnum):
    LOCKED = "LOCKED"
    UNLOCKED = "UNLOCKED"
    COMPLETED = "COMPLETED"

class DocumentNode(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(..., description="Unique identifier for the node")
    parent_id: str | None = Field(None, description="Identifier of the parent node")
    title: str = Field(..., description="Title of the node")
    summary: str | None = Field(None, description="CoD summary of the node content")
    content: str | None = Field(None, description="Full text content of the node if it is a leaf node")
    status: NodeStatus = Field(NodeStatus.LOCKED, description="Current status of the node in the learning journey")
    children_ids: list[str] = Field(default_factory=list, description="List of child node identifiers")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Metadata tags such as Time Axis, Actor, etc.")

class UserInteractionContext(BaseModel):
    model_config = ConfigDict(extra="forbid")

    node_id: str = Field(..., description="The node being interacted with")
    status: NodeStatus = Field(..., description="Current status before interaction")
    question_asked: str | None = Field(None, description="The AI generated question asked to the user")
    user_answer: str | None = Field(None, description="The user's provided answer")
    feedback: str | None = Field(None, description="AI feedback on the user's answer")
    hints_used: int = Field(0, description="Number of hints used by the user", ge=0)
