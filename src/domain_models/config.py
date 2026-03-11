from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class PipelineConfig(BaseSettings):
    model_config = SettingsConfigDict(env_nested_delimiter="__", extra="forbid")

    max_chunk_scan_size: int = Field(default=65536, ge=1024)
    trusted_model_hashes: list[str] = Field(default_factory=list)
    text_fast_model: str = Field(default="google/gemini-2.5-flash")
    text_reasoning_model: str = Field(default="deepseek/deepseek-reasoner")
    multimodal_model: str = Field(default="google/gemini-2.5-pro")


class CredentialConfig(BaseSettings):
    model_config = SettingsConfigDict(env_nested_delimiter="__", extra="forbid")

    openrouter_api_key: SecretStr | None = None
