from datetime import UTC, datetime
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, model_validator


class VerificationDetail(BaseModel):
    """
    Detailed verification result for a single claim or fact.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    claim: str = Field(..., description="The specific claim or fact extracted from the summary.")
    verdict: str = Field(
        ...,
        description="The verification verdict (e.g., 'Supported', 'Unsupported', 'Contradicted').",
    )
    reasoning: str = Field(
        ..., description="Reasoning or evidence from the source text supporting the verdict."
    )


class VerificationResult(BaseModel):
    """
    Overall verification result for a summary-source pair.
    """

    model_config = ConfigDict(extra="forbid")

    score: float = Field(
        ..., ge=0.0, le=1.0, description="Verification confidence score (0.0 to 1.0)."
    )
    details: list[VerificationDetail] = Field(
        default_factory=list, description="List of verification details for individual claims."
    )
    unsupported_claims: list[str] = Field(
        default_factory=list, description="List of claims explicitly marked as unsupported."
    )
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(UTC), description="Time of verification."
    )
    model_name: str = Field(..., description="The name of the model used for verification.")

    @model_validator(mode="after")
    def validate_score_consistency(self) -> Self:
        """
        Optional: Check if score aligns somewhat with unsupported claims.
        This is just a loose check.
        """
        if self.unsupported_claims and self.score == 1.0:
            # If there are unsupported claims, score shouldn't be perfect
            # But we won't raise error, maybe just warn or allow it if model is weird.
            # Sticking to schema validation only.
            pass
        return self
