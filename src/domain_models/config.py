import os
import re
from typing import Any

from cryptography.fernet import Fernet
from pydantic import Field, PrivateAttr, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from src.domain_models.constants import (
    DEFAULT_ACTIVE_LEARNING_SERVICE_PATH,
    DEFAULT_APP_DOMAIN,
    DEFAULT_APP_TITLE,
    DEFAULT_DOCUMENT_SERVICE_PATH,
    DEFAULT_FAST_MODEL,
    DEFAULT_GRAPH_SERVICE_PATH,
    DEFAULT_LLM_SERVICE_PATH,
    DEFAULT_MAX_CHUNK_SCAN_SIZE,
    DEFAULT_MAX_PROMPT_LENGTH,
    DEFAULT_MULTIMODAL_MODEL,
    DEFAULT_OPENROUTER_ENDPOINT,
    DEFAULT_REASONING_MODEL,
    DEFAULT_REQUESTS_PER_MINUTE_LIMIT,
)


class CredentialConfig(BaseSettings):
    """Configuration for sensitive credentials with encryption at rest."""

    model_config = SettingsConfigDict(env_nested_delimiter="__", extra="forbid")

    openrouter_api_key: SecretStr | None = None

    # Use an explicitly loaded key; no defaults allowed in production.
    _encrypted_api_key: bytes | None = PrivateAttr(default=None)

    @field_validator("openrouter_api_key")
    @classmethod
    def validate_api_key(cls, v: SecretStr | None) -> SecretStr | None:
        """Validates API key strictly against standard OpenRouter formats."""
        if v is not None:
            val = v.get_secret_value()
            if len(val) < 20:
                msg = "API key must be at least 20 characters long"
                raise ValueError(msg)
            # OpenRouter keys typically start with sk-or-v1- and contain hex/alphanumeric strings
            pattern = r"^sk-or-v1-[a-zA-Z0-9]{64}$"
            if not re.match(pattern, val):
                msg = "API key must strictly match the OpenRouter 'sk-or-v1-' 64-char alphanumeric pattern."
                raise ValueError(msg)
        return v

    def __init__(self, **data: Any) -> None:
        super().__init__(**data)

        # Load a stable encryption key strictly from environment. Fails fast if missing.
        raw_key = os.environ.get("MATOME_ENCRYPTION_KEY")
        if not raw_key:
            msg = "MATOME_ENCRYPTION_KEY environment variable must be set for secure operations."
            raise ValueError(msg)

        # Encrypt the API key at rest upon instantiation using transient key from OS environment
        if self.openrouter_api_key is not None:
            fernet = Fernet(raw_key.encode("utf-8"))
            self._encrypted_api_key = fernet.encrypt(
                self.openrouter_api_key.get_secret_value().encode("utf-8")
            )

            # Erase the raw SecretStr entirely to prevent memory inspection
            self.openrouter_api_key = None

    def get_decrypted_api_key(self) -> SecretStr | None:
        """Returns the decrypted API key securely wrapped in Pydantic's SecretStr."""
        if self._encrypted_api_key is None:
            return None

        # Load transient key to decrypt
        raw_key = os.environ.get("MATOME_ENCRYPTION_KEY")
        if not raw_key:
            msg = "MATOME_ENCRYPTION_KEY environment variable is missing during decryption phase."
            raise ValueError(msg)

        fernet = Fernet(raw_key.encode("utf-8"))
        decrypted_bytes = fernet.decrypt(self._encrypted_api_key)
        return SecretStr(decrypted_bytes.decode("utf-8"))


class PipelineConfig(BaseSettings):
    """Configuration for the document processing pipeline."""

    model_config = SettingsConfigDict(env_nested_delimiter="__", extra="forbid")

    credentials: CredentialConfig = Field(default_factory=CredentialConfig)

    max_chunk_scan_size: int = Field(default=DEFAULT_MAX_CHUNK_SCAN_SIZE)
    fast_model: str = Field(default=DEFAULT_FAST_MODEL)
    reasoning_model: str = Field(default=DEFAULT_REASONING_MODEL)
    multimodal_model: str = Field(default=DEFAULT_MULTIMODAL_MODEL)
    trusted_model_hashes: list[str] = Field(default_factory=list)

    app_domain: str = Field(default=DEFAULT_APP_DOMAIN)
    app_title: str = Field(default=DEFAULT_APP_TITLE)
    max_prompt_length: int = Field(default=DEFAULT_MAX_PROMPT_LENGTH)
    requests_per_minute_limit: int = Field(default=DEFAULT_REQUESTS_PER_MINUTE_LIMIT)
    openrouter_endpoint: str = Field(default=DEFAULT_OPENROUTER_ENDPOINT)

    # Dynamic import paths for DI resolution in production without hardcoding imports
    llm_service_path: str = Field(default=DEFAULT_LLM_SERVICE_PATH)
    document_service_path: str = Field(default=DEFAULT_DOCUMENT_SERVICE_PATH)
    graph_service_path: str = Field(default=DEFAULT_GRAPH_SERVICE_PATH)
    active_learning_service_path: str = Field(default=DEFAULT_ACTIVE_LEARNING_SERVICE_PATH)
