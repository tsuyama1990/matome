from pydantic import BaseModel, ConfigDict, Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class PipelineConfig(BaseModel):
    """
    Configuration parameters for the ingestion and processing pipeline.
    """

    model_config = ConfigDict(extra="forbid")

    max_chunk_size: int = Field(
        default=5000, ge=100, description="Maximum token size for a semantic chunk."
    )
    max_file_size_bytes: int = Field(
        default=1024 * 1024 * 50,  # 50 MB
        ge=1024,
        description="Maximum allowed file size for upload.",
    )
    clustering_random_seed: int = Field(
        default=42, description="Deterministic seed for clustering algorithms."
    )


class CredentialConfig(BaseModel):
    """
    Configuration holding external API credentials.
    """

    model_config = ConfigDict(extra="forbid")

    openrouter_api_key: SecretStr | None = Field(
        default=None, description="API key for OpenRouter AI provider."
    )


class AppConfig(BaseSettings):
    """
    Global application configuration.
    """

    model_config = SettingsConfigDict(
        env_nested_delimiter="__", extra="forbid", populate_by_name=True
    )

    environment: str = Field(
        default="development", validation_alias="APP_ENV", description="Application environment."
    )
    pipeline: PipelineConfig = Field(default_factory=PipelineConfig)
    credentials: CredentialConfig = Field(default_factory=CredentialConfig)
