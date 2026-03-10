from pydantic import BaseModel, ConfigDict, Field

from .constants import NODE_ID_PATTERN
from .enums import NodeStatus
from .types import NodeID

__all__ = [
    "AIMetadataContainer",
    "AIProcessingMetadata",
    "BestPracticeData",
    "Content",
    "ContentNode",
    "IdentityNode",
    "NodeMetadata",
    "NodeMetadataContainer",
    "NodeStatus",
    "PipelineContext",
    "SummaryNode",
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


class Content(BaseModel):
    """Encapsulates raw content entirely decoupled from node relations."""

    model_config = ConfigDict(extra="forbid")
    summary: str | None = Field(
        None, description="CoD summary of the node content", max_length=2000
    )
    text: str | None = Field(
        None, description="Full text content of the node if it is a leaf node", max_length=100000
    )


class ContentNode(BaseModel):
    """Encapsulates the content mapping of a node combining pure identity links to pure content."""

    model_config = ConfigDict(extra="forbid")

    node_id: str = Field(..., description="Link to the identity node this content belongs to")
    content: Content = Field(..., description="The raw content block")


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


class NodeMetadataContainer(BaseModel):
    model_config = ConfigDict(extra="forbid")
    node_id: str = Field(..., description="Link to the identity node")
    metadata: NodeMetadata = Field(..., description="Metadata tags such as Time Axis, Actor, etc.")


class AIMetadataContainer(BaseModel):
    model_config = ConfigDict(extra="forbid")
    node_id: str = Field(..., description="Link to the identity node")
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


class SummaryNode(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: NodeID = Field(
        ...,
        description="Unique identifier for the summary node",
    )
    title: str = Field(..., description="Title of the summary node", max_length=500)
    summary: str = Field(..., description="The summary text", max_length=2000)
    children_indices: list[str] = Field(
        default_factory=list, description="Indices/IDs of the children nodes"
    )


class PipelineContext(BaseModel):
    model_config = ConfigDict(extra="forbid")
    root_doc_id: str = Field(
        ..., description="Root document ID", max_length=100, pattern=NODE_ID_PATTERN
    )
    content: str | None = Field(default=None, description="Content to process", max_length=100000)
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
