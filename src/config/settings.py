from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppConfig(BaseSettings):
    """Core application configuration."""

    environment: str = Field(default="production", description="The application environment.")
    database_uri: SecretStr = Field(description="The URI for the operational database.")
    encryption_key: SecretStr = Field(description="A 32-byte string for BYOK encryption.")
    upload_dir: str = Field(
        default="./matome_uploads",
        description="Directory for uploaded files.",
    )

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="forbid")


class ModelConfig(BaseSettings):
    """Configuration for LLMs via OpenRouter."""

    openrouter_api_key: SecretStr = Field(description="The OpenRouter API key.")
    text_fast_model: str = Field(
        default="google/gemini-2.5-flash", description="Model for chunking and fast processing."
    )
    text_reasoning_model: str = Field(
        default="anthropic/claude-3.7-sonnet", description="Model for reasoning tasks."
    )
    multimodal_model: str = Field(
        default="openai/gpt-4o", description="Model for multimodal tasks."
    )
    embedding_model: str = Field(
        default="multi-qa-mpnet-base-dot-v1", description="Model for generating vector embeddings."
    )

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="forbid")
