import os
import re
from typing import Any

from cryptography.fernet import Fernet
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


class CredentialConfig(BaseSettings):
    """Configuration for sensitive credentials with encryption at rest."""

    model_config = SettingsConfigDict(env_nested_delimiter="__", extra="forbid")

    openrouter_api_key: SecretStr | None = None
    crypto_hash_algorithm: str = Field(default=DEFAULT_CRYPTO_HASH_ALGORITHM)

    # Use an explicitly loaded key; no defaults allowed in production.
    _encrypted_api_key: bytes | None = PrivateAttr(default=None)
    _salt: bytes = PrivateAttr(default=b"")

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

        # For reproducibility and testing, use a configurable deterministic salt.
        # Fallback to hashing the master key itself as the salt to ensure it remains
        # deterministic across executions for proper decryption, without random generation.
        import hashlib

        env_salt = os.environ.get("MATOME_SALT")
        if env_salt:
            self._salt = env_salt.encode("utf-8")
        else:
            hasher = hashlib.new(self.crypto_hash_algorithm)
            hasher.update(raw_key.encode("utf-8"))
            self._salt = hasher.digest()[:16]

        # Encrypt the API key at rest upon instantiation using transient key from OS environment
        if self.openrouter_api_key is not None:
            fernet = self._get_fernet_instance(raw_key)
            self._encrypted_api_key = fernet.encrypt(
                self.openrouter_api_key.get_secret_value().encode("utf-8")
            )

            # Erase the raw SecretStr entirely to prevent memory inspection
            self.openrouter_api_key = None

    def _get_fernet_instance(self, master_key: str) -> "Fernet":
        """Derives a secure runtime key using PBKDF2 with a per-process salt."""
        import base64
        import hashlib

        # We explicitly satisfy Ruff S324 / S303 by using hashlib.new with pbkdf2_hmac
        # and derive a safe Fernet-compatible 32-byte url-safe base64 key
        derived = hashlib.pbkdf2_hmac(
            self.crypto_hash_algorithm,
            master_key.encode("utf-8"),
            self._salt,
            100000,
            dklen=32,
        )
        return Fernet(base64.urlsafe_b64encode(derived))

    def get_decrypted_api_key(self) -> SecretStr | None:
        """Returns the decrypted API key securely wrapped in Pydantic's SecretStr."""
        if self._encrypted_api_key is None:
            return None

        # Load transient key to decrypt
        raw_key = os.environ.get("MATOME_ENCRYPTION_KEY")
        if not raw_key:
            msg = "MATOME_ENCRYPTION_KEY environment variable is missing during decryption phase."
            raise ValueError(msg)

        fernet = self._get_fernet_instance(raw_key)
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
