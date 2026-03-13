from pydantic import BaseModel, ConfigDict, Field


class PivotRequestPayload(BaseModel):
    """Payload for requesting a pivot KJ analysis."""

    axis: str = Field(
        ..., description="The multi-dimensional axis to pivot on (e.g., actor, time)."
    )

    model_config = ConfigDict(extra="forbid")
