import pytest


def test_settings_api_key_valid(
    tmp_path: pytest.TempPathFactory, monkeypatch: pytest.MonkeyPatch
) -> None:
    valid_key = "sk-or-v1-validkey12345678901234567890"
    monkeypatch.setenv("OPENROUTER_API_KEY", valid_key)
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
            pytest.raises(ConfigurationError, match="Invalid configuration state."),
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
            pytest.raises(ConfigurationError, match="Invalid configuration state."),
            provider.get_api_key(),
        ):
            pass
    finally:
        pass
