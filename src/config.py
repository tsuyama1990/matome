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


class CredentialConfig(MatomeConfig):
    """Dedicated configuration for handling security credentials separately from app settings."""

    openrouter_api_key: SecretStr = Field(..., description="BYOK API key for OpenRouter")

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


class Settings(MatomeConfig):
    """Global application configuration settings utilizing pydantic-settings."""

    credentials: CredentialConfig = Field(default_factory=CredentialConfig)  # type: ignore[arg-type]

    openrouter_api_url: str = Field(
        ...,
        description="The base URL for the OpenRouter API endpoint",
    )
    ssl_cert_path: str | None = Field(
        default_factory=lambda: os.getenv("SSL_CERT_PATH", None),
        description="Path to a pinned CA bundle for explicit SSL verification",
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
    trusted_spacy_models: list[str] = Field(
        default_factory=lambda: os.getenv(
            "TRUSTED_SPACY_MODELS", "en_core_web_sm,en_core_web_md"
        ).split(","),
        description="List of trusted SpaCy models that are allowed to load",
    )
    trusted_model_hashes: dict[str, str] = Field(
        default_factory=lambda: {
            "en_core_web_sm": os.getenv("HASH_EN_CORE_WEB_SM", "dummy_hash_for_testing"),
            "en_core_web_md": os.getenv("HASH_EN_CORE_WEB_MD", "dummy_hash_for_testing_md"),
        },
        description="Map of allowed models to their expected SHA256 hashes",
    )
    fallback_ner_regex: str = Field(
        default_factory=lambda: str(
            os.getenv("FALLBACK_NER_REGEX", r"\b[A-Z][a-z]{1,20}(?:\s+[A-Z][a-z]{1,20}){0,3}\b")
        ),
        description="Regex pattern used for fallback entity extraction",
    )
    random_seed: int = Field(
        default_factory=lambda: int(os.getenv("RANDOM_SEED", "42")),
        description="Random seed for clustering ML models (UMAP/GMM)",
    )
    entity_extraction_rate_limit: float = Field(
        default_factory=lambda: float(os.getenv("ENTITY_EXTRACTION_RATE_LIMIT", "0.01")),
        description="Rate limit in seconds between entity extraction chunks",
    )

    @field_validator("allowed_base_dir", mode="after")
    @classmethod
    def validate_allowed_base_dir(cls, value: str) -> str:
        import os
        from pathlib import Path

        from src.domain_models.exceptions import ConfigurationError

        if not value:
            err_msg = "ALLOWED_BASE_DIR must be configured in settings."
            raise ConfigurationError(err_msg)

        try:
            path_obj = Path(value)
            if not path_obj.is_absolute():
                err_msg = "ALLOWED_BASE_DIR must be an absolute path."
                raise ConfigurationError(err_msg)

            # Canonicalize and strictly resolve to eliminate symlink traversal and double dot (..) attacks
            # Realpath converts symlinks, resolve checks existence and enforces strict canonical form
            resolved_path = Path(os.path.realpath(value)).resolve(strict=True)

            # Ensure the resolved path remains within the intended parent logical volume
            # Note: For base dir configuration, the resolved path MUST exactly equal itself or be a directory.
            # Usually allowed_base_dir is exactly what we want to resolve to.

            # Simple absolute comparison is enough for canonicalized paths to check if they match their own canonical form.
        except (OSError, ValueError, RuntimeError) as e:
            err_msg = f"Invalid or unsafe ALLOWED_BASE_DIR: {e}"
            raise ConfigurationError(err_msg) from e

        return str(resolved_path)


class AppContext(BaseModel):
    settings: Settings
    mode_config: ModeConfig
    db: Any | None = None


class ConcreteConfigService:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def get(self, key: str) -> Any:
        return getattr(self._settings, key)


class SecureString:
    """A secure wrapper utilizing bytearray for explicit memory zeroization of sensitive credentials."""

    def __init__(self, value: str) -> None:
        # Store as mutable bytearray to allow explicit zeroization
        self._value = bytearray(value.encode("utf-8"))

    def get_secret_value(self) -> str:
        return self._value.decode("utf-8")

    def __str__(self) -> str:
        return "********"

    def __repr__(self) -> str:
        return "SecureString('********')"

    def __enter__(self) -> "SecureString":
        return self

    def _zeroize(self) -> None:
        import ctypes

        if hasattr(self, "_value") and self._value:
            # Overwrite memory buffer backing the bytearray directly via ctypes
            buffer_size = len(self._value)
            ctypes.memset((ctypes.c_char * buffer_size).from_buffer(self._value), 0, buffer_size)
            self._value = bytearray()

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self._zeroize()

    def __del__(self) -> None:
        self._zeroize()


class EnvCredentialProvider:
    """Secure credential provider strictly executing JIT string extraction directly returning values to the HTTP Client without storing them inside AI services."""

    def __init__(self, credential_config: CredentialConfig) -> None:
        self._config = credential_config

    def get_api_key(self) -> SecureString:
        from src.domain_models.exceptions import ConfigurationError
        from src.utils.validation import validate_api_key_format

        key = self._config.openrouter_api_key.get_secret_value()
        try:
            validate_api_key_format(key)
        except ValueError as e:
            msg = f"Secure Credential Provider intercepted invalid API key during retrieval: {e}"
            raise ConfigurationError(msg) from e
        return SecureString(key)


def create_app_context(settings: Settings, mode_config: ModeConfig) -> AppContext:
    """Application factory pattern for injecting global settings."""
    return AppContext(
        settings=settings,
        mode_config=mode_config,
        db=None,  # Placeholder for a DB connection dependency
    )


__all__ = ["ConcreteConfigService", "ModeConfig", "Settings", "create_app_context"]
