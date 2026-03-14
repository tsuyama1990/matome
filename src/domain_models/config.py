from pydantic import BaseModel, ConfigDict, Field, SecretStr, field_validator
from pydantic_core.core_schema import ValidationInfo
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
    fallback_model: str = Field(
        default="openai/gpt-4o-mini",
        min_length=1,
        description="Fallback model if the primary model fails.",
    )

    model_config = ConfigDict(extra="forbid")


class AppConfig(BaseSettings):
    """Core application configuration."""

    openrouter_api_key: SecretStr = Field(
        min_length=1,
        description="API Key for OpenRouter.",
    )
    openrouter_base_url: str = Field(
        default="https://openrouter.ai/api/v1/chat/completions",
        min_length=1,
        description="Base URL for OpenRouter API.",
    )
    tenant_id: str = Field(
        min_length=1,
        description="Tenant ID for isolating data.",
    )
    routing_rules: ModelRoutingRules = Field(
        default_factory=ModelRoutingRules,
        description="Rules for routing tasks to models.",
    )

    @field_validator("openrouter_api_key")
    @classmethod
    def validate_api_key(cls, v: SecretStr, info: ValidationInfo) -> SecretStr:
        _ = info
        import re

        val = v.get_secret_value()
        # Security: Allow various provider formats (OpenRouter, OpenAI, Anthropic, etc.)
        # Most keys are minimum 32 chars and mostly alphanumeric with hyphens or underscores
        if len(val) < 32:
            msg = "Invalid API key format: length must be at least 32 characters."
            raise ValueError(msg)

        if not re.match(r"^[A-Za-z0-9\-_]+$", val):
            msg = "Invalid API key format: contains invalid characters."
            raise ValueError(msg)

        if len(set(val)) < 8:
            msg = "Invalid API key: appears to be a dummy or repeating pattern."
            raise ValueError(msg)

        return v

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="forbid")
