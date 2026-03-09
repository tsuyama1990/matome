from typing import Any

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Centralized default root document ID for application configuration
ROOT_DOC_ID = "root_doc_1"


class Settings(BaseSettings):
    """Global application configuration settings utilizing pydantic-settings."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    mode: str = Field(
        default="production", description="Application execution mode (e.g. cli, production, test)"
    )
    openrouter_api_key: SecretStr | None = Field(
        default=None, description="BYOK API key for OpenRouter", validate_default=True
    )
    openrouter_api_url: str = Field(
        default="https://openrouter.ai/api/v1/chat/completions",
        description="The base URL for the OpenRouter API endpoint",
    )
    text_fast_model: str = Field(
        default="google/gemini-2.5-flash",
        description="Cheap, fast models with large context windows for chunking massive text, initial summarisation, tagging",
    )
    text_reasoning_model: str = Field(
        default="deepseek/deepseek-reasoner",
        description="Models with advanced logical reasoning capabilities for insight extraction, To-Be generation, web grounding",
    )
    multimodal_model: str = Field(
        default="openai/gpt-4o",
        description="Models excelling in visual understanding for complex charts in PDFs, architecture diagrams, UI mockups",
    )

    default_root_doc_id: str = Field(
        default=ROOT_DOC_ID, description="Default root document ID used in pipeline initialization"
    )

    chunk_size: int = Field(
        default=1000, description="Default character length for semantic chunking"
    )
    chunk_overlap: int = Field(
        default=100, description="Default overlap length for semantic chunking"
    )
    raptor_max_clusters: int = Field(
        default=5, description="Maximum number of GMM components in RAPTOR trees"
    )
    pipeline_timeout: float = Field(
        default=300.0, description="Pipeline execution timeout in seconds"
    )

    @field_validator("openrouter_api_key", mode="before")
    @classmethod
    def validate_api_key(cls, value: Any) -> Any:
        from src.utils.validation import validate_api_key_format

        if not value:
            return value

        # Unwrap if it's passed as a SecretStr or handle plain strings from env vars
        val_str = value.get_secret_value() if isinstance(value, SecretStr) else str(value)
        return validate_api_key_format(val_str)


def create_app_context(settings: Settings) -> dict[str, Any]:
    """Application factory pattern for injecting global settings."""
    return {
        "settings": settings,
        "mode": settings.mode,
        "db": None,  # Placeholder for a DB connection dependency
    }


__all__ = ["Settings", "create_app_context"]
