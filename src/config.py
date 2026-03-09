from typing import Any

from pydantic import Field, SecretStr, field_validator
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
    openrouter_api_key: SecretStr | None = Field(
        default=None, description="BYOK API key for OpenRouter", validate_default=True
    )
    openrouter_api_url: str = Field(
        default_factory=lambda: str(__import__("os").getenv("OPENROUTER_API_URL", "https://openrouter.ai/api/v1/chat/completions")),
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
        default_factory=lambda: str(__import__("os").getenv("DEFAULT_ROOT_DOC_ID", ROOT_DOC_ID)),
        description="Default root document ID used in pipeline initialization"
    )

    max_file_size: int = Field(
        default_factory=lambda: int(__import__("os").getenv("MAX_FILE_SIZE", 10 * 1024 * 1024)),
        description="Maximum allowed file size in bytes (default 10MB)"
    )
    allowed_base_dir: str = Field(
        default_factory=lambda: str(__import__("os").getenv("ALLOWED_BASE_DIR", str(__import__("pathlib").Path.cwd().resolve()))),
        description="Base directory allowed for file ingestion"
    )
    chunk_size: int = Field(
        default_factory=lambda: int(__import__("os").getenv("CHUNK_SIZE", 1000)),
        description="Default character length for semantic chunking"
    )
    chunk_overlap: int = Field(
        default_factory=lambda: int(__import__("os").getenv("CHUNK_OVERLAP", 100)),
        description="Default overlap length for semantic chunking"
    )
    raptor_max_clusters: int = Field(
        default_factory=lambda: int(__import__("os").getenv("RAPTOR_MAX_CLUSTERS", 5)),
        description="Maximum number of GMM components in RAPTOR trees"
    )
    pipeline_timeout: float = Field(
        default_factory=lambda: float(__import__("os").getenv("PIPELINE_TIMEOUT", 300.0)),
        description="Pipeline execution timeout in seconds"
    )
    ai_timeout: int = Field(
        default_factory=lambda: int(__import__("os").getenv("AI_TIMEOUT", 10)),
        description="Timeout for external AI API requests in seconds"
    )
    ai_retry_attempts: int = Field(
        default_factory=lambda: int(__import__("os").getenv("AI_RETRY_ATTEMPTS", 3)),
        description="Maximum number of retry attempts for AI requests"
    )
    ai_retry_min_wait: int = Field(
        default_factory=lambda: int(__import__("os").getenv("AI_RETRY_MIN_WAIT", 1)),
        description="Minimum backoff wait time in seconds"
    )
    ai_retry_max_wait: int = Field(
        default_factory=lambda: int(__import__("os").getenv("AI_RETRY_MAX_WAIT", 10)),
        description="Maximum backoff wait time in seconds"
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
