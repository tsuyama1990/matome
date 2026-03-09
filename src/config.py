from typing import Any

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from src.domain_models.constants import ROOT_DOC_ID


class Settings(BaseSettings):
    """Global application configuration settings utilizing pydantic-settings."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    mode: str = Field(
        default="production", description="Application execution mode (e.g. cli, production, test)"
    )
    openrouter_api_key: SecretStr | None = Field(
        default=None, description="BYOK API key for OpenRouter"
    )
    text_fast_model: str = Field(
        default="google/gemini-2.5-flash", description="Cheap, fast models with large context windows for chunking massive text, initial summarisation, tagging"
    )
    text_reasoning_model: str = Field(
        default="deepseek/deepseek-reasoner", description="Models with advanced logical reasoning capabilities for insight extraction, To-Be generation, web grounding"
    )
    multimodal_model: str = Field(
        default="openai/gpt-4o", description="Models excelling in visual understanding for complex charts in PDFs, architecture diagrams, UI mockups"
    )

    default_root_doc_id: str = Field(
        default=ROOT_DOC_ID, description="Default root document ID used in pipeline initialization"
    )

    default_sample_content: str = Field(
        default="This is a very long business manual about strategy. Executive approval is required if the budget > 5000.",
        description="Sample content used for execution fallback in development mode"
    )

    @classmethod
    @field_validator("openrouter_api_key", mode="before")
    def validate_api_key(cls, value: str | None) -> str | None:
        if value is not None and len(value) < 10:
            msg = "API Key must be at least 10 characters long if provided."
            raise ValueError(msg)
        return value


def create_app_context(settings: Settings) -> dict[str, Any]:
    """Application factory pattern for injecting global settings."""
    return {
        "settings": settings,
        "mode": settings.mode,
        "db": None,  # Placeholder for a DB connection dependency
    }


__all__ = ["Settings", "create_app_context"]
