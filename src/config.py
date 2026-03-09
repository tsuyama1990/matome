import os
from typing import Any

from pydantic import BaseModel, Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class MatomeConfig(BaseSettings):
    """Base configuration model class"""

    model_config = SettingsConfigDict(extra="forbid")


class ModeConfig(MatomeConfig):
    """Application mode configuration."""

    mode: str = Field(
        default="production", description="Application execution mode (e.g. cli, production, test)"
    )


class Settings(MatomeConfig):
    """Global application configuration settings utilizing pydantic-settings."""

    openrouter_api_key: SecretStr = Field(..., description="BYOK API key for OpenRouter")
    openrouter_api_url: str = Field(
        ...,
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
        default_factory=lambda: str(os.getenv("DEFAULT_ROOT_DOC_ID", "root_doc_1")),
        description="Default root document ID used in pipeline initialization",
    )

    max_file_size: int = Field(
        default_factory=lambda: int(os.getenv("MAX_FILE_SIZE", "10485760")),
        description="Maximum allowed file size in bytes (default 10MB)",
    )
    allowed_base_dir: str = Field(
        ...,
        description="Base directory allowed for file ingestion",
    )
    chunk_size: int = Field(
        default_factory=lambda: int(os.getenv("CHUNK_SIZE", "1000")),
        description="Default character length for semantic chunking",
    )
    chunk_overlap: int = Field(
        default_factory=lambda: int(os.getenv("CHUNK_OVERLAP", "100")),
        description="Default overlap length for semantic chunking",
    )
    raptor_max_clusters: int = Field(
        default_factory=lambda: int(os.getenv("RAPTOR_MAX_CLUSTERS", "5")),
        description="Maximum number of GMM components in RAPTOR trees",
    )
    pipeline_timeout: float = Field(
        default_factory=lambda: float(os.getenv("PIPELINE_TIMEOUT", "300.0")),
        description="Pipeline execution timeout in seconds",
    )
    ai_timeout: int = Field(
        default_factory=lambda: int(os.getenv("AI_TIMEOUT", "10")),
        description="Timeout for external AI API requests in seconds",
    )
    ai_retry_attempts: int = Field(
        default_factory=lambda: int(os.getenv("AI_RETRY_ATTEMPTS", "3")),
        description="Maximum number of retry attempts for AI requests",
    )
    ai_retry_min_wait: int = Field(
        default_factory=lambda: int(os.getenv("AI_RETRY_MIN_WAIT", "1")),
        description="Minimum backoff wait time in seconds",
    )
    ai_retry_max_wait: int = Field(
        default_factory=lambda: int(os.getenv("AI_RETRY_MAX_WAIT", "10")),
        description="Maximum backoff wait time in seconds",
    )
    spacy_model: str = Field(
        default_factory=lambda: str(os.getenv("SPACY_MODEL", "en_core_web_sm")),
        description="SpaCy model used for Entity Extraction",
    )
    random_seed: int = Field(
        default_factory=lambda: int(os.getenv("RANDOM_SEED", "42")),
        description="Random seed for clustering ML models (UMAP/GMM)",
    )

    @field_validator("allowed_base_dir", mode="after")
    @classmethod
    def validate_allowed_base_dir(cls, value: str) -> str:
        from pathlib import Path

        from src.domain_models.exceptions import ConfigurationError

        if not value:
            err_msg = "ALLOWED_BASE_DIR must be configured in settings."
            raise ConfigurationError(err_msg)

        if not Path(value).is_absolute():
            err_msg = "ALLOWED_BASE_DIR must be an absolute path."
            raise ConfigurationError(err_msg)
        return value

    @field_validator("openrouter_api_key", mode="after")
    @classmethod
    def validate_api_key(cls, value: SecretStr) -> SecretStr:
        from src.domain_models.exceptions import ConfigurationError
        from src.utils.validation import validate_api_key_format

        if not value:
            err_msg = "OPENROUTER_API_KEY is required"
            raise ConfigurationError(err_msg)

        val_str = value.get_secret_value()

        try:
            validate_api_key_format(val_str)
        except ValueError as e:
            raise ConfigurationError(str(e)) from e
        else:
            return value


class AppContext(BaseModel):
    settings: Settings
    mode_config: ModeConfig
    db: Any | None = None


class ConcreteConfigService:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def get(self, key: str) -> Any:
        return getattr(self._settings, key)


def create_app_context(settings: Settings, mode_config: ModeConfig) -> AppContext:
    """Application factory pattern for injecting global settings."""
    return AppContext(
        settings=settings,
        mode_config=mode_config,
        db=None,  # Placeholder for a DB connection dependency
    )


__all__ = ["ConcreteConfigService", "ModeConfig", "Settings", "create_app_context"]
