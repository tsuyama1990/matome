from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class SemanticChunk(BaseModel):
    """A semantically bounded chunk of text extracted from a document."""

    model_config = ConfigDict(extra="forbid")

    id: str
    text: str = Field(min_length=1, max_length=100000)
    metadata: dict[str, Any] = Field(default_factory=dict)

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
