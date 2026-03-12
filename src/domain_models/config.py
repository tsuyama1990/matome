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
    DEFAULT_MAX_FILE_SIZE,
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
            # Validate basic format
            if not val.startswith("sk-or-v1-"):
                msg = "API key must start with the OpenRouter 'sk-or-v1-' prefix."
                raise ValueError(msg)
        return v


    _decrypted_key_cache: SecretStr | None = PrivateAttr(default=None)

    def encrypt_key(self, crypto_service: Any) -> None:
        """Explicitly encrypts the API key after validation, wiping the raw string."""
        if self.openrouter_api_key is not None:
            self._encrypted_api_key = crypto_service.encrypt(self.openrouter_api_key)
            self.openrouter_api_key = None

    def get_decrypted_api_key(self, crypto_service: Any) -> SecretStr | None:
        """Returns the decrypted API key securely, using a cache to avoid repeated decryptions."""
        if self._encrypted_api_key is None:
            return None
        if self._decrypted_key_cache is None:
            self._decrypted_key_cache = crypto_service.decrypt(self._encrypted_api_key)
        return self._decrypted_key_cache

    def clear_cache(self) -> None:
        """Clears the decrypted key cache for security."""
        self._decrypted_key_cache = None


class PipelineConfig(BaseSettings):
    """Configuration for the document processing pipeline."""

    model_config = SettingsConfigDict(env_nested_delimiter="__", extra="forbid")

    credentials: ApiCredentials = Field(default_factory=ApiCredentials)

    max_file_size: int = Field(default=DEFAULT_MAX_FILE_SIZE)
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
    allowed_input_dir: str | None = Field(default=None)
    openrouter_ip: str | None = Field(default=None)

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
        import ipaddress
        import socket
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

        hostname = parsed.hostname
        if not hostname:
            msg = "Invalid hostname."
            raise ValueError(msg)

        # DNS Resolution Validation to prevent SSRF and DNS Rebinding
        try:
            ip = socket.gethostbyname(hostname)
        except socket.gaierror as e:
            msg = f"Could not resolve hostname {parsed.hostname}."
            raise ValueError(msg) from e

        ip_obj = ipaddress.ip_address(ip)
        if ip_obj.is_private or ip_obj.is_loopback:
            msg = f"Domain resolves to private or loopback IP ({ip})."
            raise ValueError(msg)

        # Implement DNS pinning to prevent DNS Rebinding by modifying the endpoint to use the resolved IP directly
        port = f":{parsed.port}" if parsed.port else ""
        path = parsed.path or ""
        query = f"?{parsed.query}" if parsed.query else ""
        return f"{parsed.scheme}://{ip}{port}{path}{query}"
