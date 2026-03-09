from typing import Any

from pydantic import Field, SecretStr
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


def create_app_context(settings: Settings) -> dict[str, Any]:
    """Application factory pattern for injecting global settings."""
    return {
        "settings": settings,
        "mode": settings.mode,
        "db": None,  # Placeholder for a DB connection dependency
    }


__all__ = ["Settings", "create_app_context"]
