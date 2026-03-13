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
    embedding: list[float] = Field(description="Vector embedding representation of the chunk.")
    metadata: ChunkMetadata = Field(description="Strictly typed metadata.")

    @field_validator("embedding")
    @classmethod
    def validate_embedding_dimension(cls, v: list[float]) -> list[float]:
        """Validates that the embedding matches the required dimensions and contains valid floats."""
        import math

        valid_dimensions = {256, 384, 512, 768, 1024, 1536, 2048, 3072}
        if len(v) not in valid_dimensions:
            msg = f"Embedding length {len(v)} is invalid. Must be one of: {sorted(valid_dimensions)}."
            raise ValueError(msg)

        for val in v:
            if not isinstance(val, float) and not isinstance(val, int):
                msg = "Embedding elements must be numbers."
                raise TypeError(msg)
            if math.isnan(val) or math.isinf(val):
                msg = "Embedding elements cannot be NaN or Inf."
                raise ValueError(msg)
            if not (-1.0 <= val <= 1.0):
                msg = "Embedding elements must be between -1.0 and 1.0."
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
