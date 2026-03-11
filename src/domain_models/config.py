import ctypes
from typing import Any

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class SecureString:
    """A secure string class that guarantees explicit zeroization in memory via ctypes."""

    def __init__(self, data: str) -> None:
        self._data = bytearray(data.encode("utf-8"))
        self._length = len(self._data)

    def __enter__(self) -> str:
        return self._data.decode("utf-8")

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        buffer = (ctypes.c_char * self._length).from_buffer(self._data)
        ctypes.memset(buffer, 0, self._length)


class CredentialConfig(BaseSettings):
    """Configuration for sensitive credentials."""

    model_config = SettingsConfigDict(env_nested_delimiter="__", extra="forbid")

    openrouter_api_key: SecretStr | None = None


class PipelineConfig(BaseSettings):
    """Configuration for the document processing pipeline."""

    model_config = SettingsConfigDict(env_nested_delimiter="__", extra="forbid")

    credentials: CredentialConfig = Field(default_factory=CredentialConfig)
    max_chunk_scan_size: int = 10000
    fast_model: str = "google/gemini-2.5-flash"
    reasoning_model: str = "anthropic/claude-3.7-sonnet"
    multimodal_model: str = "openai/gpt-4o"
    trusted_model_hashes: list[str] = Field(default_factory=list)
