from typing import Any, TypeAlias

from pydantic import BaseModel, ConfigDict, Field, model_validator

# Define a type alias for Metadata to improve readability and consistency.
# Using Any allows for flexibility (strings, ints, lists of tags, etc.)
Metadata: TypeAlias = dict[str, Any]


class Document(BaseModel):
    """Represents the raw input file."""

    model_config = ConfigDict(extra="forbid")

    content: str = Field(..., description="Full text content of the document.")
    metadata: Metadata = Field(
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
    metadata: Metadata = Field(
        default_factory=dict, description="Optional extra info about the chunk."
    )

    @model_validator(mode="after")
    def check_indices(self) -> "Chunk":
        """Validate that start_char_idx is less than or equal to end_char_idx."""
        if self.start_char_idx > self.end_char_idx:
            msg = (
                f"start_char_idx ({self.start_char_idx}) cannot be greater than "
                f"end_char_idx ({self.end_char_idx})"
            )
            raise ValueError(msg)
        return self
