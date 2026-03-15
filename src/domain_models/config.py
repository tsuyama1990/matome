from pydantic import BaseModel, ConfigDict, Field, SecretStr, field_validator
from pydantic_core.core_schema import ValidationInfo
from pydantic_settings import BaseSettings, SettingsConfigDict

DEFAULT_FORBIDDEN_HOSTS = ["127.0.0.1", "localhost", "0.0.0.0", "::1"]  # noqa: S104


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
    max_file_size_limit: int = Field(
        default=100 * 1024 * 1024,
        gt=0,
        description="The absolute upper boundary for max_file_size.",
    )
    file_read_chunk_size: int = Field(
        default=1024 * 1024, gt=0, description="Chunk size for file reading operations."
    )
    max_content_length: int = Field(
        default=100000,
        description="Maximum allowed character length for returned or parsed content.",
    )
    fernet_token_pattern: str = Field(
        default=r"^gAAAAA[A-Za-z0-9\-_=]+$",
        description="Regex pattern for validating Fernet tokens.",
    )
    llm_api_key_pattern: str = Field(
        default="",
        description="Regex pattern for validating external LLM API keys. Empty string disables validation.",
    )
    llm_api_key_length: int = Field(
        default=0,
        description="Exact required length of external LLM API keys. 0 disables length checking.",
    )
    max_prompt_length: int = Field(
        default=100000,
        description="Maximum allowed character length for LLM prompts.",
    )
    max_prompt_tokens: int = Field(
        default=25000,
        description="Maximum estimated token count for LLM prompts.",
    )
    llm_timeout: float = Field(
        default=30.0,
        description="Default timeout in seconds for LLM API requests.",
    )
    max_retry_attempts: int = Field(
        default=3,
        description="Maximum number of retry attempts for transient network errors.",
    )
    forbidden_internal_hosts: list[str] = Field(
        default=DEFAULT_FORBIDDEN_HOSTS,
        description="List of forbidden internal hostnames for external API calls to prevent SSRF.",
    )
    retry_min_wait: float = Field(
        default=1.0,
        description="Minimum wait time between retries in seconds.",
    )
    retry_max_wait: float = Field(
        default=10.0,
        description="Maximum wait time between retries in seconds.",
    )

    min_api_key_length: int = Field(
        default=32,
        description="Minimum character length for API keys.",
    )
    min_api_key_entropy: int = Field(
        default=8,
        description="Minimum unique character count (entropy) for API keys.",
    )
    base_api_key_pattern: str = Field(
        default=r"^[A-Za-z0-9\-_]+$",
        description="Base regex pattern for validating API keys.",
    )

    @field_validator("openrouter_api_key")
    @classmethod
    def validate_api_key(cls, v: SecretStr, info: ValidationInfo) -> SecretStr:
        import re

        val = v.get_secret_value()

        min_length = info.data.get("min_api_key_length", 32)
        min_entropy = info.data.get("min_api_key_entropy", 8)
        base_pattern = info.data.get("base_api_key_pattern", r"^[A-Za-z0-9\-_]+$")

        if len(val) < min_length:
            msg = f"Invalid API key format: length must be at least {min_length} characters."
            raise ValueError(msg)

        if not re.match(base_pattern, val):
            msg = "Invalid API key format: contains invalid characters."
            raise ValueError(msg)

        if len(set(val)) < min_entropy:
            msg = "Invalid API key: appears to be a fake or repeating pattern."
            raise ValueError(msg)

        return v

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="forbid")
