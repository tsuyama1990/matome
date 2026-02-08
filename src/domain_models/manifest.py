from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class Document(BaseModel):
    """Represents the raw input file."""

    model_config = ConfigDict(extra="forbid")

    content: str = Field(..., description="Full text content of the document.")
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Metadata associated with the document (e.g., filename)."
    )


class Chunk(BaseModel):
    """Represents a segment of text."""

    model_config = ConfigDict(extra="forbid")

    index: int = Field(..., ge=0, description="Sequential ID of the chunk.")
    text: str = Field(..., description="The actual text content of the chunk.")
    start_char_idx: int = Field(
        ..., ge=0, description="Starting character position in the original text."
    )
    end_char_idx: int = Field(
        ..., ge=0, description="Ending character position in the original text."
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Optional extra info about the chunk."
    )
