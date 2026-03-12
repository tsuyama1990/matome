"""Domain models for documents, chunks, and graph nodes."""

from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ChunkMetadata(BaseModel):
    """Metadata for a semantic chunk."""

    model_config = ConfigDict(extra="forbid")
    source_doc_id: UUID
    start_index: int = Field(..., ge=0)
    end_index: int = Field(..., ge=0)
    entities: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_indices(self) -> "ChunkMetadata":
        """Ensure start_index is strictly less than end_index."""
        if self.start_index >= self.end_index:
            msg = "start_index must be strictly less than end_index"
            raise ValueError(msg)
        return self


class SemanticChunk(BaseModel):
    """A semantic chunk of text."""

    model_config = ConfigDict(extra="forbid")
    chunk_id: UUID = Field(default_factory=uuid4)
    content: str = Field(..., min_length=1)
    metadata: ChunkMetadata


class GraphNode(BaseModel):
    """A node in the RAPTOR graph."""

    model_config = ConfigDict(extra="forbid")
    node_id: UUID = Field(default_factory=uuid4)
    level: int = Field(..., ge=0)
    summary: str
    children_ids: list[UUID] = Field(default_factory=list)
    chunk_ids: list[UUID] = Field(default_factory=list)
    is_unlocked: bool = Field(default=False)


class SourceDocument(BaseModel):
    """A source document ingested into the system."""

    model_config = ConfigDict(extra="forbid")
    document_id: UUID = Field(default_factory=uuid4)
    filename: str = Field(..., min_length=1)
    file_type: str = Field(..., min_length=1)
