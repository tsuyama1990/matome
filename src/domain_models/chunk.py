from pydantic import BaseModel, ConfigDict, Field


class ChunkMetadata(BaseModel):
    """Strictly validated metadata payload for SemanticChunks."""

    model_config = ConfigDict(extra="forbid")

    page_number: int = Field(default=1, ge=1)
    source_document: str = Field(default="unknown")
    entities_extracted: list[str] = Field(default_factory=list)


class SemanticChunk(BaseModel):
    """A semantically bounded chunk of text extracted from a document."""

    model_config = ConfigDict(extra="forbid")

    id: str
    text: str = Field(min_length=1, max_length=100000)
    metadata: ChunkMetadata = Field(default_factory=ChunkMetadata)
