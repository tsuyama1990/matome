from pydantic import BaseModel, ConfigDict, Field


class ProcessingConfig(BaseModel):
    """Configuration for text processing and chunking."""

    model_config = ConfigDict(extra="forbid")

    max_tokens: int = Field(default=500, ge=1, description="Maximum number of tokens per chunk.")
    overlap: int = Field(
        default=0, ge=0, description="Number of overlapping tokens between chunks."
    )
