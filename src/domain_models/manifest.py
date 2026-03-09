from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class NodeStatus(StrEnum):
    LOCKED = "LOCKED"
    UNLOCKED = "UNLOCKED"
    COMPLETED = "COMPLETED"


class NodeMetadata(BaseModel):
    model_config = ConfigDict(extra="forbid")
    source: str | None = Field(None, max_length=200)
    author: str | None = Field(None, max_length=100)
    category: str | None = Field(None, max_length=50)
    time_axis: str | None = Field(None, max_length=50)


class DocumentContent(BaseModel):
    model_config = ConfigDict(extra="forbid")
    summary: str | None = Field(
        None, description="CoD summary of the node content", max_length=2000
    )
    text: str | None = Field(
        None, description="Full text content of the node if it is a leaf node", max_length=100000
    )


class AIProcessingMetadata(BaseModel):
    model_config = ConfigDict(extra="forbid")
    chunk_id: str | None = Field(None, description="Semantic chunk identifier", max_length=100)
    chunk_index: int | None = Field(
        None, description="Index of semantic chunk in document flow", ge=0
    )
    entity_metadata: dict[str, str] = Field(
        default_factory=dict, description="Named Entity Recognition metadata"
    )
    hierarchical_tree: dict[str, str] = Field(
        default_factory=dict, description="UMAP/GMM clustering results tree"
    )


class DocumentNode(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(
        ...,
        description="Unique identifier for the node",
        max_length=100,
        pattern=r"^[a-zA-Z0-9_-]+$",
    )
    parent_id: str | None = Field(
        None,
        description="Identifier of the parent node",
        max_length=100,
        pattern=r"^[a-zA-Z0-9_-]+$",
    )
    title: str = Field(..., description="Title of the node", max_length=500)
    content: DocumentContent = Field(..., description="The content components of the node")
    status: NodeStatus = Field(
        NodeStatus.LOCKED, description="Current status of the node in the learning journey"
    )
    children_ids: list[str] = Field(
        default_factory=list, description="List of child node identifiers"
    )
    metadata: NodeMetadata = Field(..., description="Metadata tags such as Time Axis, Actor, etc.")

    # Adding fields mandated by auditor in FR-1.2 and FR-1.3 requirements
    ai_metadata: AIProcessingMetadata | None = Field(
        default=None, description="AI processing metadata"
    )


class UserInteractionContext(BaseModel):
    model_config = ConfigDict(extra="forbid")

    node_id: str = Field(
        ...,
        description="The node being interacted with",
        max_length=100,
        pattern=r"^[a-zA-Z0-9_-]+$",
    )
    status: NodeStatus = Field(..., description="Current status before interaction")
    question_asked: str | None = Field(
        None, description="The AI generated question asked to the user", max_length=1000
    )
    user_answer: str | None = Field(None, description="The user's provided answer", max_length=2000)
    feedback: str | None = Field(
        None, description="AI feedback on the user's answer", max_length=2000
    )
    hints_used: int = Field(0, description="Number of hints used by the user", ge=0, le=10)
