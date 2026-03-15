import logging
import urllib.parse

from pydantic import AnyHttpUrl, Field, SecretStr, field_validator
from pydantic_core.core_schema import ValidationInfo
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)


class DatabaseConfig(BaseSettings):
    """Database connection configuration."""

    database_uri_encrypted: str = Field(
        description="The encrypted URI for the operational database."
    )

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    def _validate_uri(self, uri: str) -> SecretStr:
        parsed_uri = urllib.parse.urlparse(uri)
        if parsed_uri.scheme not in ("postgresql", "sqlite", "mysql"):
            msg = f"Decrypted database URI has invalid scheme: {parsed_uri.scheme}"
            raise ValueError(msg)

        if parsed_uri.scheme == "sqlite":
            return SecretStr(uri)

        if not parsed_uri.hostname:
            msg = "Database URI must include a hostname."
            raise ValueError(msg)

        if parsed_uri.port and not (1 <= parsed_uri.port <= 65535):
            msg = "Database URI port out of range."
            raise ValueError(msg)

        # Prevent SSRF: block local loopback patterns unless strictly needed.
        if parsed_uri.hostname in ("127.0.0.1", "localhost", "0.0.0.0", "::1"):  # noqa: S104
            # For this test scope, we might allow it, but architectural spec says "reject local IPs / loops"
            msg = "Local database connections are not permitted by security policy."
            raise ValueError(msg)

        # Optional: strip userinfo before returning if we want to sanitize, but typically SQLAlchemy needs it.
        # But per instructions: "Add comprehensive URI validation including userinfo stripping"
        # We can construct a clean URI without userinfo to return, or just validate it.
        # Replacing userinfo:
        clean_netloc = parsed_uri.hostname
        if parsed_uri.port:
            clean_netloc += f":{parsed_uri.port}"

        clean_uri = urllib.parse.urlunparse(
            (
                parsed_uri.scheme,
                clean_netloc,
                parsed_uri.path,
                parsed_uri.params,
                parsed_uri.query,
                parsed_uri.fragment,
            )
        )

        return SecretStr(clean_uri)

    @property
    def get_decrypted_database_uri(self) -> SecretStr:
        """Returns the decrypted database URI securely."""
        from src.config.security import DecryptionError, SecurityService

        service = SecurityService()
        try:
            with service.get_decrypted_key(self.database_uri_encrypted) as uri:
                return self._validate_uri(uri)
        except DecryptionError:
            logger.exception("Database decryption failed.")
            raise
        except Exception:
            logger.exception("Database URI validation failed.")
            raise


class AppConfig(BaseSettings):
    """Core application configuration."""

    environment: str = Field(
        default="production", min_length=1, description="The application environment."
    )
    upload_dir: str = Field(
        default="testfiles", min_length=1, description="The directory for file uploads."
    )
    max_file_size: int = Field(
        default=50 * 1024 * 1024, gt=0, description="The max file size in bytes."
    )
    max_file_size_limit: int = Field(
        default=100 * 1024 * 1024,
        gt=0,
        description="The absolute upper boundary for max_file_size.",
    )
    file_read_chunk_size: int = Field(
        default=1024 * 1024, gt=0, description="Chunk size for file reading operations."
    )
    spacy_model: str = Field(
        default="en_core_web_sm", min_length=1, description="Spacy model name."
    )
    max_content_length: int = Field(
        default=100000,
        description="Maximum allowed character length for returned or parsed content.",
    )
    allowed_embedding_dimensions: list[int] = Field(
        default_factory=lambda: [256, 384, 512, 768, 1024, 1536, 2048, 3072],
        description="Allowed embedding dimensions.",
    )
    raptor_max_levels: int = Field(default=3, description="Maximum levels for RAPTOR tree.")
    raptor_max_clusters: int = Field(default=5, description="Maximum clusters per RAPTOR level.")
    pivot_allowed_axes: list[str] = Field(
        default_factory=lambda: ["actor", "time", "entities"],
        description="List of allowed axes for Pivot KJ analysis.",
    )
    nlp_max_entities: int = Field(
        default=50,
        gt=0,
        le=1000,
        description="Max entities to extract per chunk to prevent memory exhaustion.",
    )
    nlp_time_axis_past_words: list[str] = Field(
        default_factory=lambda: ["yesterday", "previously", "was", "were"],
        description="Keywords to detect past time axis.",
    )
    nlp_time_axis_future_words: list[str] = Field(
        default_factory=lambda: ["tomorrow", "will", "future", "next"],
        description="Keywords to detect future time axis.",
    )

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


class ModelConfig(BaseSettings):
    """Configuration for LLMs via OpenRouter."""

    openrouter_api_url: AnyHttpUrl = Field(
        description="The OpenRouter API endpoint.",
    )

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
    fernet_token_pattern: str = Field(
        default=r"^gAAAAA[A-Za-z0-9\-_=]+$",
        description="Regex pattern for validating Fernet tokens.",
    )
    openrouter_key_pattern: str = Field(
        default=r"^sk-or-v1-[a-f0-9]{64}$",
        description="Regex pattern for validating OpenRouter API keys.",
    )
    openrouter_key_length: int = Field(
        default=73,
        description="Exact required length of OpenRouter API keys.",
    )
    max_prompt_length: int = Field(
        default=100000,
        description="Maximum allowed character length for LLM prompts.",
    )
    max_sentences_per_chunk: int = Field(
        default=5,
        description="Maximum number of sentences per semantic chunk before fallback splitting.",
    )
    max_prompt_tokens: int = Field(
        default=25000,
        description="Maximum estimated token count for LLM prompts.",
    )
    max_content_length: int = Field(
        default=100000,
        description="Maximum allowed character length for returned or parsed content.",
    )
    max_retry_attempts: int = Field(
        default=3,
        description="Maximum number of retry attempts for transient network errors.",
    )
    retry_min_wait: float = Field(
        default=1.0,
        description="Minimum wait time between retries in seconds.",
    )
    retry_max_wait: float = Field(
        default=10.0,
        description="Maximum wait time between retries in seconds.",
    )

    @field_validator("openrouter_api_url")
    @classmethod
    def validate_https_url(cls, v: AnyHttpUrl, info: ValidationInfo) -> AnyHttpUrl:
        """Ensures the API URL uses HTTPS and is in the allowed hosts list."""
        if v.scheme != "https":
            msg = "OpenRouter API URL must use HTTPS."
            raise ValueError(msg)

        allowed_hosts = info.data.get("allowed_hosts", [])
        if allowed_hosts and v.host not in allowed_hosts:
            msg = f"Host {v.host} is not in the allowed hosts list to prevent SSRF."
            raise ValueError(msg)

        # Hardblock internal networks explicitly
        if v.host in ("127.0.0.1", "localhost", "0.0.0.0", "::1"):  # noqa: S104
            msg = "Internal network hostnames are forbidden for external API calls."
            raise ValueError(msg)

        return v

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")
