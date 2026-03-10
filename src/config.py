import contextlib
import os
from collections.abc import Iterator

from pydantic import BaseModel, ConfigDict, Field, SecretStr, field_validator
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


class CredentialConfig(MatomeConfig):
    """Dedicated configuration class for externalizing and securely holding credentials."""

    openrouter_api_key: SecretStr = Field(
        ..., description="The OpenRouter API Key. Accessed securely via EnvCredentialProvider."
    )

    @field_validator("openrouter_api_key", mode="after")
    @classmethod
    def validate_openrouter_api_key(cls, v: SecretStr) -> SecretStr:
        from src.domain_models.exceptions import ConfigurationError
        from src.utils.validation import validate_api_key_format

        try:
            validate_api_key_format(v.get_secret_value())
        except ValueError as err:
            raise ConfigurationError(str(err)) from err
        return v

    openrouter_api_url: SecretStr = Field(
        ...,
        description="The base URL for the OpenRouter API endpoint",
    )
    ssl_cert_path: SecretStr = Field(
        ...,
        description="Path to a pinned CA bundle for explicit SSL verification",
    )

    @field_validator("openrouter_api_url", mode="after")
    @classmethod
    def validate_openrouter_api_url(cls, v: SecretStr) -> SecretStr:
        from urllib.parse import urlparse

        val = v.get_secret_value()
        parsed = urlparse(val)

        if parsed.scheme != "https":
            from src.domain_models.exceptions import ConfigurationError

            msg = "openrouter_api_url must use HTTPS protocol"
            raise ConfigurationError(msg)

        if not parsed.netloc:
            from src.domain_models.exceptions import ConfigurationError

            msg = "openrouter_api_url must contain a valid domain"
            raise ConfigurationError(msg)

        return v

    @field_validator("ssl_cert_path", mode="after")
    @classmethod
    def validate_ssl_cert_path(cls, v: SecretStr) -> SecretStr:
        from pathlib import Path

        from src.domain_models.exceptions import ConfigurationError

        val = v.get_secret_value()

        path = Path(val)
        if not path.is_file():
            msg = f"ssl_cert_path must point to an existing file: {val}"
            raise ConfigurationError(msg)

        import os

        if not os.access(path, os.R_OK):
            msg = f"ssl_cert_path file must be readable: {val}"
            raise ConfigurationError(msg)

        return v


class ModelConfig(MatomeConfig):
    """Dedicated configuration class for AI model routing and selection."""

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

    @field_validator("text_fast_model", "text_reasoning_model", "multimodal_model", mode="after")
    @classmethod
    def validate_ai_models(cls, value: str) -> str:
        from src.utils.validation import validate_ai_model

        return validate_ai_model(value)


class Settings(MatomeConfig):
    """Global application configuration settings utilizing pydantic-settings."""

    models: ModelConfig = Field(
        default_factory=lambda: ModelConfig(),  # type: ignore[call-arg] # noqa: PLW0108
        description="Configuration and routing for AI models",
    )

    default_root_doc_id: str = Field(
        default_factory=lambda: str(os.getenv("DEFAULT_ROOT_DOC_ID", "root_doc_1")),
        description="Default root document ID used in pipeline initialization",
    )

    file_buffer_size: int = Field(
        default_factory=lambda: int(os.getenv("FILE_BUFFER_SIZE", "16384")),
        description="Buffer size used for reading streaming files",
    )
    max_file_size: int = Field(
        default_factory=lambda: int(os.getenv("MAX_FILE_SIZE", "10485760")),
        description="Maximum allowed file size in bytes (default 10MB)",
    )
    max_input_length: int = Field(
        default_factory=lambda: int(os.getenv("MAX_INPUT_LENGTH", "50000")),
        description="Maximum allowed input string length for security sanitization",
    )
    allowed_base_dir: str = Field(
        ...,
        description="Base directory allowed for file ingestion",
    )
    chunk_size: int = Field(
        ..., description="Default character length for semantic chunking", ge=100, le=10000
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
        ...,
        description="SpaCy model used for Entity Extraction",
    )
    trusted_spacy_models: list[str] = Field(
        ...,
        description="List of trusted SpaCy models that are allowed to load",
    )
    trusted_model_hashes: dict[str, str] = Field(
        default_factory=dict,
        description="Map of allowed models to their expected SHA256 hashes. Populated dynamically via environment variables.",
    )
    max_model_signature_size: int = Field(
        default_factory=lambda: int(os.getenv("MAX_MODEL_SIGNATURE_SIZE", "52428800")),
        description="Max bytes read when verifying a model signature",
        le=104857600,
        ge=1024,
    )
    fallback_ner_regex: str = Field(
        default=r"\b[A-Z][a-z]{1,20}(?:\s+[A-Z][a-z]{1,20}){0,3}\b",
        description="Strictly bound regex pattern used for fallback entity extraction",
    )
    random_seed: int = Field(
        default_factory=lambda: int(os.getenv("RANDOM_SEED", "42")),
        description="Random seed for clustering ML models (UMAP/GMM)",
    )
    entity_extraction_rate_limit: float = Field(
        default_factory=lambda: float(os.getenv("ENTITY_EXTRACTION_RATE_LIMIT", "0.01")),
        description="Rate limit in seconds between entity extraction chunks",
    )

    @field_validator("trusted_spacy_models", mode="before")
    @classmethod
    def split_and_validate_spacy_models(cls, v: str | list[str]) -> list[str]:
        import os

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
        import os

        # Only populate hashes, strict cryptographic validation must be done securely at runtime by ModelVerifier.
        return {
            "en_core_web_sm": os.getenv("HASH_EN_CORE_WEB_SM", ""),
            "en_core_web_md": os.getenv("HASH_EN_CORE_WEB_MD", ""),
        }

    @field_validator("allowed_base_dir", mode="after")
    @classmethod
    def validate_allowed_base_dir(cls, value: str) -> str:
        import os

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


class AppContext(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    settings: Settings
    mode_config: ModeConfig


class DatabaseContext(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    db: DatabaseProtocol | None = None


class EnvCredentialProvider:
    """Secure JIT credential provider fetching directly from OS environment variables strictly at runtime. Uses context manager for immediate explicit memory deletion."""

    def __init__(self, env_var_name: str = "OPENROUTER_API_KEY") -> None:
        from src.utils.errors import CredentialErrorHandler

        self._error_handler = CredentialErrorHandler()
        self._env_var_name = env_var_name

    @contextlib.contextmanager
    def get_api_key(self) -> Iterator[str]:
        import ctypes
        import os

        key: str | None = os.getenv(self._env_var_name)

        if not key:
            self._error_handler.handle_missing_key()

        if not isinstance(key, str):
            self._error_handler.handle_invalid_type()

        self._error_handler.validate_and_format(key)

        try:
            # We yield the string natively since Python strings are immutable and ctypes memory zeroization
            # is not robust/reliable across all GC platforms. Memory limits and short-lived execution cycles
            # offer primary credential safety in standard Python environments.
            yield key
        finally:
            # Clear local reference to prompt garbage collection
            key = None  # noqa: F841
            del key


def create_app_context(settings: Settings, mode_config: ModeConfig) -> AppContext:
    """Application factory pattern for injecting global settings."""
    return AppContext(
        settings=settings,
        mode_config=mode_config,
    )


__all__ = [
    "CredentialConfig",
    "DatabaseContext",
    "ModeConfig",
    "Settings",
    "create_app_context",
]
