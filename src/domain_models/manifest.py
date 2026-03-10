from pydantic import BaseModel, ConfigDict, Field

from .constants import MAX_CONTENT_LENGTH, NODE_ID_PATTERN
from .enums import NodeStatus

__all__ = [
    "AIProcessingMetadata",
    "BestPracticeData",
    "ContentNode",
    "IdentityNode",
    "NodeMetadata",
    "NodeStatus",
    "PipelineContext",
    "UserInteractionContext",
    "WisdomData",
]


class BestPracticeData(BaseModel):
    model_config = ConfigDict(extra="forbid")
    content: str = Field(..., description="Best practice text content", max_length=2000)


class WisdomData(BaseModel):
    model_config = ConfigDict(extra="forbid")
    content: str = Field(..., description="Wisdom text content", max_length=2000)


class NodeMetadata(BaseModel):
    model_config = ConfigDict(extra="forbid")
    source: str | None = Field(None, max_length=200)
    author: str | None = Field(None, max_length=100)
    category: str | None = Field(None, max_length=50)
    time_axis: str | None = Field(None, max_length=50)
    best_practices: list[BestPracticeData] = Field(
        default_factory=list, description="Extracted best practices"
    )
    wisdom_data: list[WisdomData] = Field(
        default_factory=list, description="Aggregated wisdom points"
    )


class ContentNode(BaseModel):
    """Encapsulates the content of a node entirely separated from its identity structure."""

    model_config = ConfigDict(extra="forbid")

    node_id: str = Field(..., description="Link to the identity node this content belongs to")
    summary: str | None = Field(
        None, description="CoD summary of the node content", max_length=2000
    )
    text: str | None = Field(
        None,
        description="Full text content of the node if it is a leaf node",
        max_length=MAX_CONTENT_LENGTH,
    )


class AIProcessingMetadata(BaseModel):
    model_config = ConfigDict(extra="forbid")
    chunk_id: str | None = Field(
        None, description="Semantic chunk identifier", max_length=100, pattern=NODE_ID_PATTERN
    )
    chunk_index: int | None = Field(
        None, description="Index of semantic chunk in document flow", ge=0
    )
    entity_metadata: dict[str, str] = Field(
        default_factory=dict, description="Named Entity Recognition metadata"
    )
    hierarchical_tree: dict[str, str] = Field(
        default_factory=dict, description="UMAP/GMM clustering results tree"
    )


class MetadataContainer(BaseModel):
    """Container grouping all metadata classes to follow SRP strictly outside of IdentityNode."""

    model_config = ConfigDict(extra="forbid")

    metadata: NodeMetadata = Field(..., description="Metadata tags such as Time Axis, Actor, etc.")
    ai_metadata: AIProcessingMetadata = Field(..., description="AI processing metadata")


class IdentityNode(BaseModel):
    """Identity and structure properties of a node in the graph, completely independent of content."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(
        ...,
        description="Unique identifier for the node",
        max_length=100,
        pattern=NODE_ID_PATTERN,
    )
    parent_id: str | None = Field(
        None,
        description="Identifier of the parent node",
        max_length=100,
        pattern=NODE_ID_PATTERN,
    )
    title: str = Field(..., description="Title of the node", max_length=500)
    status: NodeStatus = Field(
        NodeStatus.LOCKED, description="Current status of the node in the learning journey"
    )


class PipelineContext(BaseModel):
    model_config = ConfigDict(extra="forbid")
    root_doc_id: str = Field(
        ..., description="Root document ID", max_length=100, pattern=NODE_ID_PATTERN
    )
    content: str | None = Field(
        default=None, description="Content to process", max_length=MAX_CONTENT_LENGTH
    )
    file_path: str | None = Field(default=None, description="Path to the file to process")


class UserInteractionContext(BaseModel):
    model_config = ConfigDict(extra="forbid")

    node_id: str = Field(
        ...,
        description="The node being interacted with",
        max_length=100,
        pattern=NODE_ID_PATTERN,
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
