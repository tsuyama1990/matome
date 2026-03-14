from pydantic import BaseModel, ConfigDict, Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class ModelRoutingRules(BaseModel):
    """Routing rules for different model tasks."""

    text_fast_model: str = Field(
        default="google/gemini-2.5-flash",
        min_length=1,
        description="Model for chunking and fast processing.",
    )
    text_reasoning_model: str = Field(
        default="deepseek/deepseek-reasoner",
        min_length=1,
        description="Model for reasoning tasks.",
    )
    multimodal_model: str = Field(
        default="google/gemini-2.5-pro",
        min_length=1,
        description="Model for multimodal tasks.",
    )

    model_config = ConfigDict(extra="forbid")


class AppConfig(BaseSettings):
    """Core application configuration."""

    openrouter_api_key: SecretStr = Field(
        description="API Key for OpenRouter.",
    )
    tenant_id: str = Field(
        min_length=1,
        description="Tenant ID for isolating data.",
    )
    routing_rules: ModelRoutingRules = Field(
        default_factory=ModelRoutingRules,
        description="Rules for routing tasks to models.",
    )

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="forbid")
