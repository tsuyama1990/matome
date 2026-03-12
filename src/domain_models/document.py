from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field


class ChunkMetadata(BaseModel):
    model_config = ConfigDict(extra="forbid")
    source_doc_id: UUID = Field(default_factory=uuid4)
    start_index: int = Field(..., ge=0)
    end_index: int = Field(..., ge=0)
