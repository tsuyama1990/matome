from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field


class IdentityNode(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: UUID = Field(default_factory=uuid4)
    parent_id: UUID | None = None
    children_ids: list[UUID] = Field(default_factory=list)
    tags: dict[str, str] = Field(default_factory=dict)
    locked: bool = True


class ContentNode(BaseModel):
    model_config = ConfigDict(extra="forbid")
    raw_text: str = Field(min_length=0)
    summary: str | None = None
    entities: list[str] = Field(default_factory=list)


class DocumentNode(BaseModel):
    model_config = ConfigDict(extra="forbid")
    identity: IdentityNode
    content: ContentNode
