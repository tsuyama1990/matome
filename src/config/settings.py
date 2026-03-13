from pydantic import AnyHttpUrl, Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppConfig(BaseSettings):
    """Core application configuration."""

    environment: str = Field(
        default="production", min_length=1, description="The application environment."
    )
    database_uri: SecretStr = Field(description="The URI for the operational database.")
    upload_dir: str = Field(
        default="testfiles", min_length=1, description="The directory for file uploads."
    )
    max_file_size: int = Field(
        default=50 * 1024 * 1024, gt=0, description="The max file size in bytes."
    )

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="forbid")


class ModelConfig(BaseSettings):
    """Configuration for LLMs via OpenRouter."""

    openrouter_api_url: AnyHttpUrl = Field(
        description="The OpenRouter API endpoint.",
    )

    @field_validator("openrouter_api_url")
    @classmethod
    def validate_https_url(cls, v: AnyHttpUrl) -> AnyHttpUrl:
        """Ensures the API URL uses HTTPS."""
        if v.scheme != "https":
            msg = "OpenRouter API URL must use HTTPS."
            raise ValueError(msg)
        return v
    text_fast_model: str = Field(
        description="Model for chunking and fast processing.",
    )
    text_reasoning_model: str = Field(
        description="Model for reasoning tasks.",
    )
    multimodal_model: str = Field(
        description="Model for multimodal tasks."
    )
    llm_timeout: float = Field(
        default=30.0, gt=0.0, description="The default timeout for LLM API requests in seconds."
    )
    allowed_hosts: list[str] = Field(
        default_factory=lambda: ["openrouter.ai"],
        description="List of allowed hostnames for external API calls to prevent SSRF.",
    )

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="forbid")
