from pydantic import AnyHttpUrl, Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppConfig(BaseSettings):
    """Core application configuration."""

    environment: str = Field(default="production", min_length=1, description="The application environment.")
    database_uri: SecretStr = Field(description="The URI for the operational database.")
    upload_dir: str = Field(default="testfiles", min_length=1, description="The directory for file uploads.")
    max_file_size: int = Field(default=50 * 1024 * 1024, gt=0, description="The max file size in bytes.")

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="forbid")


class ModelConfig(BaseSettings):
    """Configuration for LLMs via OpenRouter."""

    openrouter_api_url: AnyHttpUrl = Field(
        default="https://openrouter.ai/api/v1/chat/completions",  # type: ignore[assignment]
        description="The OpenRouter API endpoint.",
    )
    text_fast_model: str = Field(
        default="google/gemini-2.5-flash", min_length=1, description="Model for chunking and fast processing."
    )
    text_reasoning_model: str = Field(
        default="anthropic/claude-3.7-sonnet", min_length=1, description="Model for reasoning tasks."
    )
    multimodal_model: str = Field(
        default="openai/gpt-4o", min_length=1, description="Model for multimodal tasks."
    )
    llm_timeout: float = Field(
        default=30.0, gt=0.0, description="The default timeout for LLM API requests in seconds."
    )
    allowed_hosts: list[str] = Field(
        default_factory=lambda: ["openrouter.ai"],
        description="List of allowed hostnames for external API calls to prevent SSRF.",
    )

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="forbid")
