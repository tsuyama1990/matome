import re
from typing import Any

from pydantic import Field, PrivateAttr, SecretStr, ValidationInfo, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from src.domain_models.constants import (
    DEFAULT_ACTIVE_LEARNING_SERVICE_PATH,
    DEFAULT_ALLOWED_API_DOMAINS,
    DEFAULT_APP_DOMAIN,
    DEFAULT_APP_TITLE,
    DEFAULT_CRYPTO_HASH_ALGORITHM,
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


class CryptoConfig(BaseSettings):
    """Configuration for cryptographic settings separated from sensitive credential state."""

    model_config = SettingsConfigDict(env_nested_delimiter="__", extra="forbid")

    crypto_hash_algorithm: str = Field(default=DEFAULT_CRYPTO_HASH_ALGORITHM)


class ApiCredentials(BaseSettings):
    """Configuration for sensitive credentials interacting natively with CryptoService for encryption at rest."""

    model_config = SettingsConfigDict(env_nested_delimiter="__", extra="forbid")

    openrouter_api_key: SecretStr | None = None
    crypto_config: CryptoConfig = Field(default_factory=CryptoConfig)

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

        from src.infrastructure.crypto import CryptoService

        # Encrypt the API key at rest upon instantiation using transient key from OS environment
        if self.openrouter_api_key is not None:
            crypto_service = CryptoService(self.crypto_config)
            self._encrypted_api_key = crypto_service.encrypt(self.openrouter_api_key)

            # Erase the raw SecretStr entirely to prevent memory inspection
            self.openrouter_api_key = None

    def get_decrypted_api_key(self) -> SecretStr | None:
        """Returns the decrypted API key securely wrapped in Pydantic's SecretStr."""
        if self._encrypted_api_key is None:
            return None

        from src.infrastructure.crypto import CryptoService

        crypto_service = CryptoService(self.crypto_config)
        return crypto_service.decrypt(self._encrypted_api_key)


class PipelineConfig(BaseSettings):
    """Configuration for the document processing pipeline."""

    model_config = SettingsConfigDict(env_nested_delimiter="__", extra="forbid")

    credentials: ApiCredentials = Field(default_factory=ApiCredentials)

    max_chunk_scan_size: int = Field(default=DEFAULT_MAX_CHUNK_SCAN_SIZE)
    fast_model: str = Field(default=DEFAULT_FAST_MODEL)
    reasoning_model: str = Field(default=DEFAULT_REASONING_MODEL)
    multimodal_model: str = Field(default=DEFAULT_MULTIMODAL_MODEL)
    trusted_model_hashes: list[str] = Field(default_factory=list)

    app_domain: str = Field(default=DEFAULT_APP_DOMAIN)
    app_title: str = Field(default=DEFAULT_APP_TITLE)
    max_prompt_length: int = Field(default=DEFAULT_MAX_PROMPT_LENGTH)
    requests_per_minute_limit: int = Field(default=DEFAULT_REQUESTS_PER_MINUTE_LIMIT)

    # Define allowed_api_domains before openrouter_endpoint so it is available in info.data
    allowed_api_domains: list[str] = Field(
        default_factory=lambda: list(DEFAULT_ALLOWED_API_DOMAINS)
    )
    openrouter_endpoint: str = Field(default=DEFAULT_OPENROUTER_ENDPOINT)

    # Dynamic import paths for DI resolution in production without hardcoding imports
    llm_service_path: str = Field(default=DEFAULT_LLM_SERVICE_PATH)
    document_service_path: str = Field(default=DEFAULT_DOCUMENT_SERVICE_PATH)
    graph_service_path: str = Field(default=DEFAULT_GRAPH_SERVICE_PATH)
    active_learning_service_path: str = Field(default=DEFAULT_ACTIVE_LEARNING_SERVICE_PATH)

    @field_validator("app_domain", "app_title")
    @classmethod
    def validate_no_crlf(cls, v: str) -> str:
        """Validates HTTP headers to strictly reject Carriage Return and Line Feed (CRLF) characters."""
        if "\r" in v or "\n" in v:
            msg = "CRLF injection detected in header value."
            raise ValueError(msg)
        return v

    @field_validator("openrouter_endpoint")
    @classmethod
    def validate_allowed_api_domains(cls, v: str, info: ValidationInfo) -> str:
        """Enforces strict HTTPS and validates URLs against a whitelist of allowed domains (SSRF protection)."""
        import urllib.parse

        parsed = urllib.parse.urlparse(v)
        if parsed.scheme != "https":
            msg = "Endpoint must use HTTPS."
            raise ValueError(msg)
        domain = f"{parsed.scheme}://{parsed.netloc}"
        allowed = info.data.get("allowed_api_domains", DEFAULT_ALLOWED_API_DOMAINS)
        if domain not in allowed:
            msg = f"Domain {domain} is not in the allowed API domains whitelist."
            raise ValueError(msg)
        return v
