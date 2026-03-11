import secrets
from pathlib import Path

from pydantic import SecretStr
from pydantic_settings import SettingsConfigDict

from src.domain_models import CredentialConfig, PipelineConfig, SecureString


def test_secure_string_zeroization() -> None:
    """Mathematically guarantees that sensitive credentials utilize the secure memory encapsulation logic."""
    secret_value = secrets.token_hex(16)

    secure_str = SecureString(secret_value)

    with secure_str as val:
        # Check that we received a memoryview
        assert isinstance(val, memoryview)
        # Check that we can read from the memoryview and reconstruct the string explicitly
        assert val.tobytes().decode("utf-8") == secret_value

    # After exiting the context manager, the bytearray backing the secure string should be zeroed out
    assert all(b == 0 for b in secure_str._data)


def test_credential_config_loading(tmp_path: Path) -> None:
    """Verifies that CredentialConfig correctly reads .env variables using tmp_path."""
    env_file = tmp_path / ".env"
    env_file.write_text('OPENROUTER_API_KEY="sk-or-v1-123456789"\n')

    # We must patch os.environ temporarily for pydantic_settings to pick up the file or env
    # Since we want to test native loading, we configure the env_file in the model
    class TestCredentialConfig(CredentialConfig):
        model_config = SettingsConfigDict(env_file=str(env_file), extra="forbid")

    config = TestCredentialConfig()

    assert config.openrouter_api_key is not None
    assert isinstance(config.openrouter_api_key, SecretStr)
    assert config.openrouter_api_key.get_secret_value() == "sk-or-v1-123456789"


def test_pipeline_config_defaults() -> None:
    """Verifies PipelineConfig defaults."""
    config = PipelineConfig()
    assert config.max_chunk_scan_size == 10000
    assert config.fast_model == "google/gemini-2.5-flash"
    assert config.reasoning_model == "anthropic/claude-3.7-sonnet"
    assert config.multimodal_model == "openai/gpt-4o"
    assert config.trusted_model_hashes == []
    assert config.credentials is not None
    assert config.credentials.openrouter_api_key is None
