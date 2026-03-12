"""Configuration and Cryptographic models."""

import contextlib
from collections.abc import Iterator

from cryptography.fernet import Fernet
from pydantic import BaseModel, ConfigDict, Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class CryptoConfig(BaseSettings):
    """Cryptographic configuration."""

    matome_encryption_key: str = Field(..., alias="MATOME_ENCRYPTION_KEY")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


class CryptoService:
    """Service for encryption and decryption."""

    def __init__(self, key: str) -> None:
        """Initialize with a Fernet key."""
        self._fernet = Fernet(key.encode("utf-8"))

    def encrypt(self, data: str) -> str:
        """Encrypt string data."""
        return self._fernet.encrypt(data.encode("utf-8")).decode("utf-8")

    def decrypt(self, data: str) -> str:
        """Decrypt string data."""
        return self._fernet.decrypt(data.encode("utf-8")).decode("utf-8")


class ApiCredentials(BaseModel):
    """API credentials storing encrypted key in memory."""

    encrypted_key: str

    model_config = ConfigDict(extra="forbid")

    @contextlib.contextmanager
    def get_decrypted_key(self, crypto_service: CryptoService) -> Iterator[str | None]:
        """Yield the decrypted key temporarily."""
        decrypted_key: str | None = None
        try:
            decrypted_key = crypto_service.decrypt(self.encrypted_key)
            yield decrypted_key
        finally:
            decrypted_key = None  # Ensure reference is cleared


class CredentialConfig(BaseSettings):
    """Credential configuration managing the API key securely."""

    openrouter_api_key: SecretStr = Field(..., alias="OPENROUTER_API_KEY")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    def get_api_credentials(self, crypto_service: CryptoService) -> ApiCredentials:
        """Encrypt the raw API key and return ApiCredentials."""
        raw_key = self.openrouter_api_key.get_secret_value()
        encrypted_key = crypto_service.encrypt(raw_key)
        return ApiCredentials(encrypted_key=encrypted_key)


class PipelineConfig(BaseSettings):
    """Pipeline configuration parameters."""

    llm_gateway_path: str = Field(
        default="src.infrastructure.llm_gateway.LLMGateway",
        description="Dynamic import path for LLM Gateway",
    )
    vector_repo_path: str = Field(
        default="src.infrastructure.vector_store.VectorDBRepository",
        description="Dynamic import path for Vector DB Repository",
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )
