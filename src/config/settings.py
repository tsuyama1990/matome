from pydantic import AnyHttpUrl, Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppConfig(BaseSettings):
    """Core application configuration."""

    environment: str = Field(
        default="production", min_length=1, description="The application environment."
    )
    database_uri_encrypted: str = Field(
        description="The encrypted URI for the operational database."
    )
    upload_dir: str = Field(
        default="testfiles", min_length=1, description="The directory for file uploads."
    )
    max_file_size: int = Field(
        default=50 * 1024 * 1024, gt=0, description="The max file size in bytes."
    )
    spacy_model: str = Field(
        default="en_core_web_sm", min_length=1, description="Spacy model name."
    )
    allowed_embedding_dimensions: list[int] = Field(
        default_factory=lambda: [256, 384, 512, 768, 1024, 1536, 2048, 3072],
        description="Allowed embedding dimensions.",
    )

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="forbid")

    @property
    def get_decrypted_database_uri(self) -> SecretStr:
        """Returns the decrypted database URI securely."""
        from src.config.security import SecurityService

        service = SecurityService()
        with service.get_decrypted_key(self.database_uri_encrypted) as uri:
            # Add basic validation that it looks like a URL
            if not uri.startswith(("postgresql://", "sqlite://", "mysql://")):
                msg = "Decrypted database URI has invalid scheme."
                raise ValueError(msg)
            return SecretStr(uri)


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
    multimodal_model: str = Field(description="Model for multimodal tasks.")
    llm_timeout: float = Field(
        default=30.0, gt=0.0, description="The default timeout for LLM API requests in seconds."
    )
    allowed_hosts: list[str] = Field(
        description="List of allowed hostnames for external API calls to prevent SSRF.",
    )

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")
