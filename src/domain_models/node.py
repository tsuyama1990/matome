from pydantic import BaseModel, ConfigDict, Field


class IdentityNode(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    parent_id: str | None = None
    tags: dict[str, str] = Field(default_factory=dict)


class ContentNode(BaseModel):
    model_config = ConfigDict(extra="forbid")

    text: str
    summary: str | None = None
    entities: list[str] = Field(default_factory=list)


class DocumentNode(BaseModel):
    model_config = ConfigDict(extra="forbid")

    identity: IdentityNode
    content: ContentNode
