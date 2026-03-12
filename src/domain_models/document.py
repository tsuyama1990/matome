from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ChunkMetadata(BaseModel):
    """Metadata schema for a semantic chunk with strictly forbidden extra fields."""

    source_file: str = Field(description="The original source file name.")
    page_number: int | None = Field(
        default=None, description="The page number where the chunk originated."
    )
    extracted_entities: list[str] = Field(
        default_factory=list, description="List of recognized entities."
    )
    time_axis: str | None = Field(default=None, description="Time axis tags.")
    actor_axis: str | None = Field(default=None, description="System actors axis tags.")

    model_config = ConfigDict(extra="forbid")


class SemanticChunk(BaseModel):
    """Fundamental unit of meaning, representing a single chunk of text."""

    id: UUID = Field(description="Unique identifier for the chunk.")
    content: str = Field(description="The text content.")
    embedding: list[float] = Field(
        default_factory=list, description="Vector embedding representation of the chunk."
    )
    metadata: ChunkMetadata = Field(description="Strictly typed metadata.")

    @field_validator("content")
    @classmethod
    def validate_content_length(cls, v: str) -> str:
        """Validates that the content is not empty."""
        if len(v) == 0:
            msg = "Chunk content cannot be empty."
            raise ValueError(msg)
        return v

    @field_validator("embedding")
    @classmethod
    def validate_embedding_dimension(cls, v: list[float]) -> list[float]:
        """Validates that if the embedding is provided, it matches the required dimensions."""
        if v and len(v) not in (768, 1536):
            msg = "Embedding must be empty or a valid length (e.g., 768 or 1536)."
            raise ValueError(msg)
        return v

    model_config = ConfigDict(extra="forbid")


class RaptorNode(BaseModel):
    """A node in the hierarchical summary tree."""

    node_id: str = Field(description="Unique identifier for the node.")
    level: int = Field(description="Tree depth level of the node.")
    children_ids: list[str] = Field(default_factory=list, description="IDs of child nodes.")
    summarized_content: str = Field(description="The highly dense summary of the node's cluster.")
    is_unlocked: bool = Field(default=False, description="Whether the node is unlocked in the UI.")

    @field_validator("level")
    @classmethod
    def validate_level(cls, v: int) -> int:
        """Validates that the node depth does not exceed maximum threshold."""
        if v > 10:
            msg = "Node level exceeds maximum depth threshold."
            raise ValueError(msg)
        return v

    model_config = ConfigDict(extra="forbid")


class EnrichedDocument(BaseModel):
    """The complete aggregated document representing chunks and the RAPTOR tree."""

    document_id: UUID = Field(description="The unique identifier for the document.")
    original_text: str = Field(description="The raw text of the entire document.")
    chunks: list[SemanticChunk] = Field(
        default_factory=list, description="The list of semantic chunks."
    )
    raptor_nodes: list[RaptorNode] = Field(
        default_factory=list, description="The root nodes of the RAPTOR tree."
    )

    model_config = ConfigDict(extra="forbid")
