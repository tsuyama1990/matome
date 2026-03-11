import os
from typing import Any

from cryptography.fernet import Fernet
from pydantic import Field, PrivateAttr, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class CredentialConfig(BaseSettings):
    """Configuration for sensitive credentials with encryption at rest."""

    model_config = SettingsConfigDict(env_nested_delimiter="__", extra="forbid")

    openrouter_api_key: SecretStr | None = None

    # Use an explicitly loaded key; no defaults allowed in production.
    _encryption_key: bytes = PrivateAttr()
    _encrypted_api_key: bytes | None = PrivateAttr(default=None)

    @field_validator("openrouter_api_key")
    @classmethod
    def validate_api_key(cls, v: SecretStr | None) -> SecretStr | None:
        """Validates API key format and length."""
        if v is not None:
            val = v.get_secret_value()
            if len(val) < 20:
                msg = "API key must be at least 20 characters long"
                raise ValueError(msg)
            if not val.startswith("sk-or-"):
                msg = "API key must start with 'sk-or-'"
                raise ValueError(msg)
        return v

    def __init__(self, **data: Any) -> None:
        super().__init__(**data)

        # Load a stable encryption key strictly from environment. Fails fast if missing.
        raw_key = os.environ.get("MATOME_ENCRYPTION_KEY")
        if not raw_key:
            msg = "MATOME_ENCRYPTION_KEY environment variable must be set for secure operations."
            raise ValueError(msg)

        self._encryption_key = raw_key.encode("utf-8")

        # Encrypt the API key at rest upon instantiation
        if self.openrouter_api_key is not None:
            fernet = Fernet(self._encryption_key)
            self._encrypted_api_key = fernet.encrypt(
                self.openrouter_api_key.get_secret_value().encode("utf-8")
            )

            # Erase the raw SecretStr entirely to prevent memory inspection
            self.openrouter_api_key = None

    def get_decrypted_api_key(self) -> SecretStr | None:
        """Returns the decrypted API key securely wrapped in Pydantic's SecretStr."""
        if self._encrypted_api_key is None:
            return None
        fernet = Fernet(self._encryption_key)
        decrypted_bytes = fernet.decrypt(self._encrypted_api_key)
        return SecretStr(decrypted_bytes.decode("utf-8"))


class PipelineConfig(BaseSettings):
    """Configuration for the document processing pipeline."""

    model_config = SettingsConfigDict(env_nested_delimiter="__", extra="forbid")

    credentials: CredentialConfig = Field(default_factory=CredentialConfig)
    max_chunk_scan_size: int = 10000
    fast_model: str = "google/gemini-2.5-flash"
    reasoning_model: str = "anthropic/claude-3.7-sonnet"
    multimodal_model: str = "openai/gpt-4o"
    trusted_model_hashes: list[str] = Field(default_factory=list)

    # Dynamic import paths for DI resolution in production without hardcoding imports
    llm_service_path: str = "src.interfaces.LLMProtocol"
    document_service_path: str = "src.interfaces.DocumentProcessingService"
    graph_service_path: str = "src.interfaces.KnowledgeGraphService"
    active_learning_service_path: str = "src.interfaces.ActiveLearningService"
