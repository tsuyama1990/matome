import contextlib
from collections.abc import Generator

from cryptography.fernet import Fernet
from pydantic import BaseModel, ConfigDict, Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class CryptoConfig(BaseSettings):
    model_config = SettingsConfigDict(extra="forbid", env_file=".env", env_file_encoding="utf-8")
    matome_encryption_key: str = Field(..., alias="MATOME_ENCRYPTION_KEY", pattern=r'^[A-Za-z0-9+/_=-]{43}=$')


class CredentialConfig(BaseSettings):
    model_config = SettingsConfigDict(extra="forbid", env_file=".env", env_file_encoding="utf-8")
    openrouter_api_key: SecretStr = Field(..., alias="OPENROUTER_API_KEY")

    @contextlib.contextmanager
    def yield_and_clear_secret(self) -> Generator[str, None, None]:
        secret = self.openrouter_api_key.get_secret_value()
        try:
            yield secret
        finally:
            self.openrouter_api_key = SecretStr('')


class PipelineConfig(BaseSettings):
    model_config = SettingsConfigDict(extra="forbid", env_file=".env", env_file_encoding="utf-8")
    max_file_size_bytes: int = Field(default=10 * 1024 * 1024) # 10MB


class ApiCredentials(BaseModel):
    model_config = ConfigDict(extra="forbid")
    encrypted_key: SecretStr


class CryptoService:
    def __init__(self, key: str) -> None:
        if not key or len(key) != 44:
            msg = 'Invalid encryption key'
            raise ValueError(msg)
        self._fernet = Fernet(key.encode("utf-8"))

    def encrypt(self, data: str) -> str:
        return self._fernet.encrypt(data.encode("utf-8")).decode("utf-8")

    def decrypt(self, data: str) -> str:
        return self._fernet.decrypt(data.encode("utf-8")).decode("utf-8")
