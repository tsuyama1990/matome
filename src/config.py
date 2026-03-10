import contextlib
import os
from collections.abc import Iterator

from pydantic import BaseModel, ConfigDict, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from src.domain_models.interfaces import DatabaseProtocol


class MatomeConfig(BaseSettings):
    """Base configuration model class"""

    model_config = SettingsConfigDict(extra="forbid")


class ModeConfig(MatomeConfig):
    """Application mode configuration."""

    mode: str = Field(
        default="production", description="Application execution mode (e.g. cli, production, test)"
    )


class AIConfig(BaseModel):
    """Dedicated configuration class for AI model routing and logic."""

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
    ai_timeout: int = Field(
        default=10,
        description="Timeout for external AI API requests in seconds",
    )
    ai_retry_attempts: int = Field(
        default=3,
        description="Maximum number of retry attempts for AI requests",
    )
    ai_retry_min_wait: int = Field(
        default=1,
        description="Minimum backoff wait time in seconds",
    )
    ai_retry_max_wait: int = Field(
        default=10,
        description="Maximum backoff wait time in seconds",
    )


class FileProcessingConfig(BaseModel):
    """Dedicated configuration class for file ingestion and processing limits."""

    file_buffer_size: int = Field(
        default=16384,
        description="Buffer size used for reading streaming files",
    )
    max_file_size: int = Field(
        default=10485760,
        description="Maximum allowed file size in bytes (default 10MB)",
    )
    allowed_base_dir: str = Field(
        ...,
        description="Base directory allowed for file ingestion",
    )
    chunk_size: int = Field(
        ..., description="Default character length for semantic chunking", ge=100, le=10000
    )
    chunk_overlap: int = Field(
        default=100,
        description="Default overlap length for semantic chunking",
    )

    @field_validator("allowed_base_dir", mode="after")
    @classmethod
    def validate_allowed_base_dir(cls, value: str) -> str:

        from src.domain_models.exceptions import ConfigurationError

        if not value:
            msg = "ALLOWED_BASE_DIR must be configured in settings."
            raise ConfigurationError(msg)

        if len(value) > 4096:
            msg = "ALLOWED_BASE_DIR path too long"
            raise ConfigurationError(msg)

        try:
            from pathlib import Path

            expected_parent = os.getenv("MATOME_BASE_DATA_DIR", str(Path.cwd()))

            path_obj = Path(value)

            # Explicitly reject symlinks before canonicalization to prevent symlink traversal attacks
            if path_obj.is_symlink():
                msg = "Symlinks are strictly prohibited for ALLOWED_BASE_DIR."
                raise ConfigurationError(msg)

            # Canonicalize path using os.path.realpath securely
            canonical_path = os.path.realpath(str(path_obj))

            if not Path(canonical_path).is_absolute():
                msg = "ALLOWED_BASE_DIR must be an absolute path."
                raise ConfigurationError(msg)

            if not Path(canonical_path).is_dir():
                msg = "ALLOWED_BASE_DIR must be a directory."
                raise ConfigurationError(msg)

            # Enforce strictly that canonicalized path remains within the required commonpath parent
            common = os.path.commonpath([canonical_path, expected_parent])
            if common != expected_parent:
                msg = "ALLOWED_BASE_DIR outside expected parent."
                raise ConfigurationError(msg)

            if not os.access(canonical_path, os.R_OK):
                msg = "No read permission on ALLOWED_BASE_DIR."
                raise ConfigurationError(msg)

        except (OSError, ValueError, RuntimeError) as e:
            msg = f"Invalid or unsafe ALLOWED_BASE_DIR: {e}"
            raise ConfigurationError(msg) from e

        # Ensure trailing slash normalization
        return canonical_path + "/" if not canonical_path.endswith("/") else canonical_path


class SecurityConfig(BaseModel):
    """Dedicated configuration class for security constraints and ML signature validation."""

    max_input_length: int = Field(
        default=50000,
        description="Maximum allowed input string length for security sanitization",
    )
    max_model_signature_size: int = Field(
        default=52428800,
        description="Max bytes read when verifying a model signature",
        le=104857600,
        ge=1024,
    )
    prompt_injection_threshold: float = Field(
        default=0.9,
        description="Threshold for prompt injection detection (0.8 - 1.0)",
        ge=0.8,
        le=1.0,
    )


class MLConfig(BaseModel):
    """Dedicated configuration class for ML clustering, Entity Extraction, and Spacy models."""

    spacy_model: str = Field(
        ...,
        description="SpaCy model used for Entity Extraction",
    )
    trusted_spacy_models: list[str] = Field(
        ...,
        description="List of trusted SpaCy models that are allowed to load",
    )
    trusted_model_hashes: dict[str, str] = Field(
        default_factory=dict,
        description="Map of allowed models to their expected SHA256 hashes.",
    )

    @field_validator("trusted_spacy_models", mode="before")
    @classmethod
    def split_and_validate_spacy_models(cls, v: str | list[str]) -> list[str]:

        from src.domain_models.exceptions import ConfigurationError

        values = v.split(",") if isinstance(v, str) else v

        allowed_env = os.getenv("ALLOWED_SPACY_MODELS", "en_core_web_sm,en_core_web_md")
        allowed_whitelist = {model.strip() for model in allowed_env.split(",") if model.strip()}

        parsed_values = []
        for model in values:
            model_clean = model.strip()
            if not model_clean:
                continue
            if model_clean not in allowed_whitelist:
                msg = f"Untrusted ML Model configured: {model_clean}. Only verified models ({allowed_env}) are allowed."
                raise ConfigurationError(msg)
            parsed_values.append(model_clean)

        if not parsed_values:
            msg = "TRUSTED_SPACY_MODELS cannot be empty."
            raise ConfigurationError(msg)
        return parsed_values

    @field_validator("trusted_model_hashes", mode="before")
    @classmethod
    def populate_and_validate_hashes(cls, _v: dict[str, str]) -> dict[str, str]:

        # Only populate hashes, strict cryptographic validation must be done securely at runtime by ModelVerifier.
        return {
            "en_core_web_sm": os.getenv("HASH_EN_CORE_WEB_SM", ""),
            "en_core_web_md": os.getenv("HASH_EN_CORE_WEB_MD", ""),
        }

    fallback_ner_regex: str = Field(
        default=r"\b[A-Z][a-z]{1,20}(?:\s+[A-Z][a-z]{1,20}){0,3}\b",
        description="Strictly bound regex pattern used for fallback entity extraction",
    )
    random_seed: int = Field(
        default=42,
        description="Random seed for clustering ML models (UMAP/GMM)",
    )
    entity_extraction_rate_limit: float = Field(
        default=0.01,
        description="Rate limit in seconds between entity extraction chunks",
    )
    raptor_max_clusters: int = Field(
        default=5,
        description="Maximum number of GMM components in RAPTOR trees",
    )


class PipelineConfig(BaseModel):
    """Dedicated configuration class for orchestrator pipeline limits."""

    default_root_doc_id: str = Field(
        default="root_doc_1",
        description="Default root document ID used in pipeline initialization",
    )
    pipeline_timeout: float = Field(
        default=300.0,
        description="Pipeline execution timeout in seconds",
    )


class AppContext(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    ai: AIConfig
    file: FileProcessingConfig
    security: SecurityConfig
    ml: MLConfig
    pipeline: PipelineConfig
    mode_config: ModeConfig


class DatabaseContext(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    db: DatabaseProtocol | None = None


class EnvOpenRouterConfigProvider:
    """Secure JIT credential and URL provider fetching directly from OS environment variables strictly at runtime."""

    def __init__(self) -> None:
        from src.utils.errors import CredentialErrorHandler

        self._error_handler = CredentialErrorHandler()

    def get_api_url(self) -> str:
        import os
        from urllib.parse import urlparse

        url = os.getenv("OPENROUTER_API_URL")
        if not url:
            from src.domain_models.exceptions import ConfigurationError

            msg = "OPENROUTER_API_URL is missing."
            raise ConfigurationError(msg)

        parsed = urlparse(url)
        if parsed.scheme != "https":
            from src.domain_models.exceptions import ConfigurationError

            msg = "openrouter_api_url must use HTTPS protocol"
            raise ConfigurationError(msg)

        if not parsed.netloc:
            from src.domain_models.exceptions import ConfigurationError

            msg = "openrouter_api_url must contain a valid domain"
            raise ConfigurationError(msg)
        return url

    @contextlib.contextmanager
    def get_api_key(self) -> Iterator[str]:
        import os

        key: str | None = os.getenv("OPENROUTER_API_KEY")

        if not key:
            self._error_handler.handle_missing_key()

        if not isinstance(key, str):
            self._error_handler.handle_invalid_type()

        self._error_handler.validate_and_format(key)

        try:
            yield key
        finally:
            # Clear local reference to prompt garbage collection
            key = None
            del key


def create_app_context(
    ai: AIConfig,
    file: FileProcessingConfig,
    security: SecurityConfig,
    ml: MLConfig,
    pipeline: PipelineConfig,
    mode_config: ModeConfig,
) -> AppContext:
    """Application factory pattern for injecting global settings."""
    return AppContext(
        ai=ai,
        file=file,
        security=security,
        ml=ml,
        pipeline=pipeline,
        mode_config=mode_config,
    )


__all__ = [
    "AIConfig",
    "AppContext",
    "DatabaseContext",
    "EnvOpenRouterConfigProvider",
    "FileProcessingConfig",
    "MLConfig",
    "ModeConfig",
    "PipelineConfig",
    "SecurityConfig",
    "create_app_context",
]
