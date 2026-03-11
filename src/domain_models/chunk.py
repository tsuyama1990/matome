from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class SemanticChunk(BaseModel):
    """A semantically bounded chunk of text extracted from a document."""

    model_config = ConfigDict(extra="forbid")

    id: str
    text: str = Field(min_length=1)
    metadata: dict[str, Any] = Field(default_factory=dict)
