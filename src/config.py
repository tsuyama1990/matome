import os
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from src.domain_models.constants import ROOT_DOC_ID


class MatomeConfig(BaseSettings):
    """Base configuration model class"""

    model_config = SettingsConfigDict(extra="ignore")


class Settings(MatomeConfig):
    """Global application configuration settings utilizing pydantic-settings."""

    mode: str = Field(
        default="production", description="Application execution mode (e.g. cli, production, test)"
    )
    openrouter_api_key: SecretStr = Field(
        ..., description="BYOK API key for OpenRouter"
    )
    openrouter_api_url: str = Field(
        default_factory=lambda: str(os.getenv("OPENROUTER_API_URL", "https://openrouter.ai/api/v1/chat/completions")),
        description="The base URL for the OpenRouter API endpoint",
    )
    text_fast_model: str = Field(
        ...,
        description="Cheap, fast models with large context windows for chunking massive text, initial summarisation, tagging",
    )
    text_reasoning_model: str = Field(
        ...,
        description="Models with advanced logical reasoning capabilities for insight extraction, To-Be generation, web grounding",
    )
    multimodal_model: str = Field(
        ...,
        description="Models excelling in visual understanding for complex charts in PDFs, architecture diagrams, UI mockups",
    )

    default_root_doc_id: str = Field(
        default_factory=lambda: str(os.getenv("DEFAULT_ROOT_DOC_ID", ROOT_DOC_ID)),
        description="Default root document ID used in pipeline initialization"
    )

    max_file_size: int = Field(
        default_factory=lambda: int(os.getenv("MAX_FILE_SIZE", "10485760")),
        description="Maximum allowed file size in bytes (default 10MB)"
    )
    allowed_base_dir: str = Field(
        default_factory=lambda: str(Path(os.getenv("ALLOWED_BASE_DIR", "."))),
        description="Base directory allowed for file ingestion"
    )
    chunk_size: int = Field(
        default_factory=lambda: int(os.getenv("CHUNK_SIZE", "1000")),
        description="Default character length for semantic chunking"
    )
    chunk_overlap: int = Field(
        default_factory=lambda: int(os.getenv("CHUNK_OVERLAP", "100")),
        description="Default overlap length for semantic chunking"
    )
    raptor_max_clusters: int = Field(
        default_factory=lambda: int(os.getenv("RAPTOR_MAX_CLUSTERS", "5")),
        description="Maximum number of GMM components in RAPTOR trees"
    )
    pipeline_timeout: float = Field(
        default_factory=lambda: float(os.getenv("PIPELINE_TIMEOUT", "300.0")),
        description="Pipeline execution timeout in seconds"
    )
    ai_timeout: int = Field(
        default_factory=lambda: int(os.getenv("AI_TIMEOUT", "10")),
        description="Timeout for external AI API requests in seconds"
    )
    ai_retry_attempts: int = Field(
        default_factory=lambda: int(os.getenv("AI_RETRY_ATTEMPTS", "3")),
        description="Maximum number of retry attempts for AI requests"
    )
    ai_retry_min_wait: int = Field(
        default_factory=lambda: int(os.getenv("AI_RETRY_MIN_WAIT", "1")),
        description="Minimum backoff wait time in seconds"
    )
    ai_retry_max_wait: int = Field(
        default_factory=lambda: int(os.getenv("AI_RETRY_MAX_WAIT", "10")),
        description="Maximum backoff wait time in seconds"
    )

    @field_validator("allowed_base_dir", mode="after")
    @classmethod
    def validate_allowed_base_dir(cls, value: str) -> str:
        from src.domain_models.exceptions import ConfigurationError
        if not value:
            err_msg = "ALLOWED_BASE_DIR must be configured in settings."
            raise ConfigurationError(err_msg)
        return value

    @field_validator("openrouter_api_key", mode="before")
    @classmethod
    def validate_api_key(cls, value: Any) -> Any:
        from src.domain_models.exceptions import ConfigurationError
        from src.utils.validation import validate_api_key_format

        if not value:
            err_msg = "OPENROUTER_API_KEY is required"
            raise ConfigurationError(err_msg)

        # Unwrap if it's passed as a SecretStr or handle plain strings from env vars
        val_str = value.get_secret_value() if isinstance(value, SecretStr) else str(value)

        try:
            return validate_api_key_format(val_str)
        except ValueError as e:
            raise ConfigurationError(str(e)) from e




class AppContext(BaseModel):
    settings: Settings
    mode: str
    db: Any | None = None


def create_app_context(settings: Settings) -> AppContext:
    """Application factory pattern for injecting global settings."""
    return AppContext(
        settings=settings,
        mode=settings.mode,
        db=None,  # Placeholder for a DB connection dependency
    )


__all__ = ["Settings", "create_app_context"]
