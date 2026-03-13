import re

from pydantic import BaseModel, ConfigDict, Field, field_validator
from pydantic_core.core_schema import ValidationInfo


class PivotRequestPayload(BaseModel):
    """
    Payload for requesting a pivot KJ analysis.
    Supported axes: 'actor', 'time', 'entities'.
    """

    axis: str = Field(
        ...,
        min_length=1,
        max_length=50,
        description="The multi-dimensional axis to pivot on (e.g., actor, time, entities).",
    )

    @field_validator("axis")
    @classmethod
    def validate_axis_format(cls, v: str, info: ValidationInfo) -> str:
        """Validates that the axis string is alphanumeric and safe from injection."""
        _ = info
        v = v.strip().lower()
        if not re.match(r"^[a-zA-Z0-9_-]+$", v):
            msg = "Axis must contain only alphanumeric characters, dashes, or underscores."
            raise ValueError(msg)
        return v

    model_config = ConfigDict(extra="forbid")
