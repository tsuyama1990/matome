from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class NodeState(StrEnum):
    """The valid states for a KnowledgeNode."""

    LOCKED = "Locked"
    UNLOCKED = "Unlocked"


class KnowledgeNode(BaseModel):
    """A node representing a core concept within the Summary Tree."""

    model_config = ConfigDict(extra="forbid")

    id: str
    title: str
    summary: str
    state: NodeState = Field(default=NodeState.LOCKED)
    children_ids: list[str] = Field(default_factory=list)


class SummaryTree(BaseModel):
    """The hierarchical representation of knowledge nodes."""

    model_config = ConfigDict(extra="forbid")

    root_node_id: str
    nodes: dict[str, KnowledgeNode] = Field(default_factory=dict)
