from pydantic import BaseModel, ConfigDict, Field, field_validator

from src.domain_models.constants import DEFAULT_MAX_CHUNK_SCAN_SIZE


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
    text: str = Field(min_length=1, max_length=DEFAULT_MAX_CHUNK_SCAN_SIZE)
    metadata: ChunkMetadata = Field(default_factory=ChunkMetadata)

    @field_validator("text")
    @classmethod
    def validate_text_encoding(cls, v: str) -> str:
        """Enforces that the string strictly conforms to UTF-8 without decoding errors."""
        try:
            # Pydantic strings are python strings, but we ensure it can be encoded strictly
            v.encode("utf-8", errors="strict")
        except UnicodeEncodeError as e:
            msg = "SemanticChunk text must be strictly UTF-8 encoded"
            raise ValueError(msg) from e
        return v
