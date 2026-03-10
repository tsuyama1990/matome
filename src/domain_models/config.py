from pydantic import BaseModel, ConfigDict, Field, SecretStr


class CredentialConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    openrouter_api_key: SecretStr | None = None


class PipelineConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    max_chunk_scan_size: int = Field(default=65536, ge=1024)
    trusted_model_hashes: list[str] = Field(default_factory=list)
    text_fast_model: str = Field(default="google/gemini-2.5-flash")
    text_reasoning_model: str = Field(default="deepseek/deepseek-reasoner")
    multimodal_model: str = Field(default="google/gemini-2.5-pro")
