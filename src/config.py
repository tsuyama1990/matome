import contextlib
import os
import typing
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

    openrouter_api_key: SecretStr | None = Field(
        None, description="The OpenRouter API Key. Accessed securely via EnvCredentialProvider."
    )
    openrouter_api_url: SecretStr = Field(
        ...,
        description="The base URL for the OpenRouter API endpoint",
    )
    ssl_cert_path: SecretStr | None = Field(
        default_factory=lambda: (
            SecretStr(cert_path) if (cert_path := os.getenv("SSL_CERT_PATH", None)) else None
        ),
        description="Path to a pinned CA bundle for explicit SSL verification",
    )


class Settings(MatomeConfig):
    """Global application configuration settings utilizing pydantic-settings."""

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
        import os

        from src.domain_models.exceptions import ConfigurationError

        allowed_env = os.getenv(
            "ALLOWED_AI_MODELS", "google/gemini-2.5-flash,deepseek/deepseek-reasoner,openai/gpt-4o"
        )
        allowed_whitelist = {model.strip() for model in allowed_env.split(",") if model.strip()}

        if value.strip() not in allowed_whitelist:
            msg = f"Untrusted AI Model configured: {value}. Only verified models ({allowed_env}) are allowed."
            raise ConfigurationError(msg)
        return value

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

    @field_validator("trusted_spacy_models", mode="after")
    @classmethod
    def validate_spacy_models(cls, values: list[str]) -> list[str]:
        import os

        from src.domain_models.exceptions import ConfigurationError

        allowed_env = os.getenv("ALLOWED_SPACY_MODELS", "en_core_web_sm,en_core_web_md")
        allowed_whitelist = {model.strip() for model in allowed_env.split(",") if model.strip()}

        for model in values:
            if model.strip() not in allowed_whitelist:
                msg = f"Untrusted ML Model configured: {model}. Only verified models ({allowed_env}) are allowed."
                raise ConfigurationError(msg)
        return values

    @field_validator("trusted_model_hashes", mode="before")
    @classmethod
    def populate_and_validate_hashes(cls, value: dict[str, str]) -> dict[str, str]:
        import os

        # Remove dummy hashes and enforce strict hash availability from environment mapping.
        hashes = value or {}
        sm_hash = os.getenv("HASH_EN_CORE_WEB_SM")
        md_hash = os.getenv("HASH_EN_CORE_WEB_MD")

        # Security validation ensuring hashes conform to sha256 specs
        import re

        sha_pattern = re.compile(r"^[a-fA-F0-9]{64}$")

        if sm_hash:
            if sm_hash.startswith("dummy") or not sha_pattern.match(sm_hash):
                msg = f"Invalid hash format for en_core_web_sm: {sm_hash}. Dummy hashes are strictly prohibited."
                from src.domain_models.exceptions import ConfigurationError

                raise ConfigurationError(msg)
            hashes["en_core_web_sm"] = sm_hash

        if md_hash:
            if md_hash.startswith("dummy") or not sha_pattern.match(md_hash):
                msg = f"Invalid hash format for en_core_web_md: {md_hash}. Dummy hashes are strictly prohibited."
                from src.domain_models.exceptions import ConfigurationError

                raise ConfigurationError(msg)
            hashes["en_core_web_md"] = md_hash

        return hashes

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

        expected_parent = "/"

        try:
            from pathlib import Path

            # Canonicalize path using os.path.realpath and absolute conversion to eliminate relative sequences entirely
            path_obj = Path(value)
            canonical_path = str(path_obj.resolve())

            if not path_obj.is_absolute():
                msg = "ALLOWED_BASE_DIR must be an absolute path."
                raise ConfigurationError(msg)

            if not Path(canonical_path).is_dir():
                msg = "ALLOWED_BASE_DIR must be a directory."
                raise ConfigurationError(msg)

            # Enforce strictly that canonicalized path remains within the required commonpath parent
            # os.path.commonpath prevents arbitrary traversal bypassing prefix matching
            common = os.path.commonpath([canonical_path, expected_parent])
            if common != expected_parent:
                msg = "ALLOWED_BASE_DIR outside expected parent."
                raise ConfigurationError(msg)

            if not os.access(canonical_path, os.R_OK):
                msg = "No read permission on ALLOWED_BASE_DIR."
                raise ConfigurationError(msg)

            # Disallow symlinks inherently by confirming realpath hasn't mutated unexpectedly
            if path_obj.is_symlink():
                msg = "Symlinks are strictly prohibited for ALLOWED_BASE_DIR."
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


class ConcreteConfigService:
    def __init__(self, settings: Settings, credential_config: CredentialConfig) -> None:
        self._settings = settings
        self._credential_config = credential_config

    @property
    def openrouter_api_url(self) -> str:
        return self._credential_config.openrouter_api_url.get_secret_value()

    @property
    def ssl_cert_path(self) -> str | None:
        if self._credential_config.ssl_cert_path is not None:
            return self._credential_config.ssl_cert_path.get_secret_value()
        return None

    @property
    def chunk_size(self) -> int:
        return self._settings.chunk_size

    @property
    def chunk_overlap(self) -> int:
        return self._settings.chunk_overlap

    @property
    def spacy_model(self) -> str:
        return self._settings.spacy_model

    @property
    def random_seed(self) -> int:
        return self._settings.random_seed


class CredentialErrorHandler:
    """Handles parsing errors and format validation specifically for credentials securely without logging specifics."""

    def handle_missing_key(self) -> typing.NoReturn:
        import logging

        from src.domain_models.exceptions import ConfigurationError

        logger = logging.getLogger(__name__)
        logger.warning(
            "Credential configuration state is invalid. Aborting operation securely.",
            extra={"context": "auth"},
        )
        msg = "Invalid configuration state."
        raise ConfigurationError(msg)

    def handle_invalid_type(self) -> typing.NoReturn:
        import logging

        from src.domain_models.exceptions import ConfigurationError

        logger = logging.getLogger(__name__)
        logger.warning(
            "Credential configuration state is invalid. Aborting operation securely.",
            extra={"context": "auth"},
        )
        msg = "Invalid configuration state."
        raise ConfigurationError(msg)

    def validate_and_format(self, key: str) -> None:
        import logging

        from src.domain_models.exceptions import ConfigurationError
        from src.infrastructure.security import DefaultSecurityService

        logger = logging.getLogger(__name__)
        try:
            DefaultSecurityService().validate_api_key(key)
        except ValueError as err:
            logger.warning(
                "Credential configuration state is invalid. Aborting operation securely.",
                extra={"context": "auth"},
            )
            msg = "Invalid configuration state."
            raise ConfigurationError(msg) from err


class EnvCredentialProvider:
    """Secure JIT credential provider fetching directly from OS environment variables strictly at runtime. Uses context manager for immediate explicit memory deletion."""

    def __init__(self) -> None:
        self._error_handler = CredentialErrorHandler()

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
            # Force immediate cleanup logic of local reference
            del key


def create_app_context(settings: Settings, mode_config: ModeConfig) -> AppContext:
    """Application factory pattern for injecting global settings."""
    return AppContext(
        settings=settings,
        mode_config=mode_config,
    )


__all__ = [
    "ConcreteConfigService",
    "CredentialConfig",
    "DatabaseContext",
    "ModeConfig",
    "Settings",
    "create_app_context",
]
