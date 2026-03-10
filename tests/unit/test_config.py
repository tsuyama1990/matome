import pytest


def test_settings_ssl_cert_path(
    tmp_path: pytest.TempPathFactory, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Missing required fields should raise error
    import os

    from pydantic_core._pydantic_core import ValidationError

    from src.config import Settings
    os.environ["MATOME_BASE_DATA_DIR"] = str(tmp_path)
    with pytest.raises(ValidationError):
        Settings(allowed_base_dir=str(tmp_path))

    dummy_cert = tmp_path / "dummy.pem"  # type: ignore
    dummy_cert.write_text("cert")

    from src.config import CredentialConfig
    creds = CredentialConfig(
        openrouter_api_url="https://mock",
        openrouter_api_key="sk-or-v1-validkey12345678901234567890",
        ssl_cert_path=str(dummy_cert)
    )

    settings = Settings(
        allowed_base_dir=str(tmp_path),
        text_fast_model="google/gemini-2.5-flash",
        text_reasoning_model="deepseek/deepseek-reasoner",
        multimodal_model="openai/gpt-4o",
        chunk_size=1000,
        spacy_model="en_core_web_sm",
        trusted_spacy_models=["en_core_web_sm", "en_core_web_md"]
    )
    assert creds.ssl_cert_path.get_secret_value() == str(dummy_cert)

def test_settings_api_key_valid(
    tmp_path: pytest.TempPathFactory, monkeypatch: pytest.MonkeyPatch
) -> None:
    valid_key = "sk-or-v1-validkey12345678901234567890"
    monkeypatch.setenv("OPENROUTER_API_KEY", valid_key)
    monkeypatch.setenv("SKIP_ACTIVE_KEY_VALIDATION", "true")
    try:
        from src.config import EnvCredentialProvider

        provider = EnvCredentialProvider()
        with provider.get_api_key() as secure_key:
            assert secure_key == valid_key
    finally:
        pass


def test_settings_api_key_invalid_length(
    tmp_path: pytest.TempPathFactory, monkeypatch: pytest.MonkeyPatch
) -> None:
    from src.config import EnvCredentialProvider
    from src.domain_models.exceptions import ConfigurationError

    monkeypatch.setenv("OPENROUTER_API_KEY", "short")
    try:
        provider = EnvCredentialProvider()
        with (
            pytest.raises(ConfigurationError, match="API Key validation failed"),
            provider.get_api_key(),
        ):
            pass
    finally:
        pass


def test_settings_api_key_invalid_format(
    tmp_path: pytest.TempPathFactory, monkeypatch: pytest.MonkeyPatch
) -> None:
    from src.config import EnvCredentialProvider
    from src.domain_models.exceptions import ConfigurationError

    monkeypatch.setenv(
        "OPENROUTER_API_KEY", "invalid_key_with_spaces_too_long_to_pass_length_check"
    )
    try:
        provider = EnvCredentialProvider()
        with (
            pytest.raises(ConfigurationError, match="API Key validation failed"),
            provider.get_api_key(),
        ):
            pass
    finally:
        pass
