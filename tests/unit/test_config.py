import typing

import pytest


def test_openrouter_provider_validation(monkeypatch: pytest.MonkeyPatch) -> None:
    from src.config import EnvOpenRouterConfigProvider
    from src.domain_models.exceptions import ConfigurationError

    provider = EnvOpenRouterConfigProvider()

    # Missing URL
    monkeypatch.delenv("OPENROUTER_API_URL", raising=False)
    with pytest.raises(ConfigurationError, match="OPENROUTER_API_URL is missing"):
        provider.get_api_url()

    # Invalid URL scheme
    monkeypatch.setenv("OPENROUTER_API_URL", "http://mock.com")
    with pytest.raises(ConfigurationError, match="must use HTTPS"):
        provider.get_api_url()

    # Invalid URL domain
    monkeypatch.setenv("OPENROUTER_API_URL", "https://")
    with pytest.raises(ConfigurationError, match="must contain a valid domain"):
        provider.get_api_url()

    # Valid URL
    monkeypatch.setenv("OPENROUTER_API_URL", "https://openrouter.ai/api/v1")
    assert provider.get_api_url() == "https://openrouter.ai/api/v1"


def test_settings_advanced_validation(
    tmp_path: typing.Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    import os

    from src.config import AppContext
    from src.domain_models.exceptions import ConfigurationError

    os.environ["HASH_EN_CORE_WEB_SM"] = "a" * 64
    os.environ["HASH_EN_CORE_WEB_MD"] = "b" * 64
    monkeypatch.setenv("MATOME_BASE_DATA_DIR", str(tmp_path))

    # Test invalid spacy model
    from src.config import (
        AIConfig,
        FileProcessingConfig,
        MLConfig,
        ModeConfig,
        PipelineConfig,
        SecurityConfig,
    )

    ai_cfg = AIConfig(
        text_fast_model="google/gemini-2.5-flash",
        text_reasoning_model="deepseek/deepseek-reasoner",
        multimodal_model="openai/gpt-4o",
    )

    with pytest.raises(ConfigurationError):
        AppContext(
            ai=ai_cfg,
            file=FileProcessingConfig(
                allowed_base_dir=str(tmp_path), chunk_size=1000, chunk_overlap=100
            ),
            ml=MLConfig(spacy_model="invalid_model", trusted_spacy_models=["invalid_model"]),
            security=SecurityConfig(),
            pipeline=PipelineConfig(),
            mode_config=ModeConfig(),
        )

    # Test empty spacy models
    with pytest.raises(ConfigurationError):
        AppContext(
            ai=ai_cfg,
            file=FileProcessingConfig(
                allowed_base_dir=str(tmp_path), chunk_size=1000, chunk_overlap=100
            ),
            ml=MLConfig(
                spacy_model="en_core_web_sm", trusted_spacy_models=typing.cast(list[str], "")
            ),
            security=SecurityConfig(),
            pipeline=PipelineConfig(),
            mode_config=ModeConfig(),
        )

    # Test empty base dir
    with pytest.raises(ConfigurationError):
        AppContext(
            ai=ai_cfg,
            file=FileProcessingConfig(allowed_base_dir="", chunk_size=1000, chunk_overlap=100),
            ml=MLConfig(
                spacy_model="en_core_web_sm",
                trusted_spacy_models=["en_core_web_sm", "en_core_web_md"],
            ),
            security=SecurityConfig(),
            pipeline=PipelineConfig(),
            mode_config=ModeConfig(),
        )

    # Test base dir symlink
    symlink_dir = tmp_path / "symlink"
    target_dir = tmp_path / "target"
    target_dir.mkdir()
    symlink_dir.symlink_to(target_dir)

    with pytest.raises(ConfigurationError):
        AppContext(
            ai=ai_cfg,
            file=FileProcessingConfig(
                allowed_base_dir=str(symlink_dir), chunk_size=1000, chunk_overlap=100
            ),
            ml=MLConfig(
                spacy_model="en_core_web_sm",
                trusted_spacy_models=["en_core_web_sm", "en_core_web_md"],
            ),
            security=SecurityConfig(),
            pipeline=PipelineConfig(),
            mode_config=ModeConfig(),
        )

    # Test base dir relative path
    with pytest.raises(ConfigurationError):
        AppContext(
            ai=ai_cfg,
            file=FileProcessingConfig(
                allowed_base_dir="relative/path", chunk_size=1000, chunk_overlap=100
            ),
            ml=MLConfig(
                spacy_model="en_core_web_sm",
                trusted_spacy_models=["en_core_web_sm", "en_core_web_md"],
            ),
            security=SecurityConfig(),
            pipeline=PipelineConfig(),
            mode_config=ModeConfig(),
        )

    # Test base dir file instead of directory
    file_path = tmp_path / "file.txt"
    file_path.write_text("file")
    with pytest.raises(ConfigurationError):
        AppContext(
            ai=ai_cfg,
            file=FileProcessingConfig(
                allowed_base_dir=str(file_path), chunk_size=1000, chunk_overlap=100
            ),
            ml=MLConfig(
                spacy_model="en_core_web_sm",
                trusted_spacy_models=["en_core_web_sm", "en_core_web_md"],
            ),
            security=SecurityConfig(),
            pipeline=PipelineConfig(),
            mode_config=ModeConfig(),
        )

    # Test base dir no read perms
    no_read_dir = tmp_path / "noreaddir"
    no_read_dir.mkdir()
    no_read_dir.chmod(0o000)
    try:
        with pytest.raises(ConfigurationError):
            AppContext(
                ai=ai_cfg,
                file=FileProcessingConfig(
                    allowed_base_dir=str(no_read_dir), chunk_size=1000, chunk_overlap=100
                ),
                ml=MLConfig(
                    spacy_model="en_core_web_sm",
                    trusted_spacy_models=["en_core_web_sm", "en_core_web_md"],
                ),
                security=SecurityConfig(),
                pipeline=PipelineConfig(),
                mode_config=ModeConfig(),
            )
    finally:
        no_read_dir.chmod(0o700)

    # Test string too long
    with pytest.raises(ConfigurationError):
        AppContext(
            ai=ai_cfg,
            file=FileProcessingConfig(
                allowed_base_dir="a" * 4097, chunk_size=1000, chunk_overlap=100
            ),
            ml=MLConfig(
                spacy_model="en_core_web_sm",
                trusted_spacy_models=["en_core_web_sm", "en_core_web_md"],
            ),
            security=SecurityConfig(),
            pipeline=PipelineConfig(),
            mode_config=ModeConfig(),
        )


def test_settings_api_key_valid(tmp_path: typing.Any, monkeypatch: pytest.MonkeyPatch) -> None:
    valid_key = "sk-or-v1-validkey12345678901234567890"
    monkeypatch.setenv("OPENROUTER_API_KEY", valid_key)
    monkeypatch.setenv("SKIP_ACTIVE_KEY_VALIDATION", "true")
    try:
        from src.config import EnvOpenRouterConfigProvider

        provider = EnvOpenRouterConfigProvider()
        with provider.get_api_key() as secure_key:
            assert secure_key == valid_key
    finally:
        pass


def test_settings_api_key_invalid_length(
    tmp_path: typing.Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    from src.config import EnvOpenRouterConfigProvider
    from src.domain_models.exceptions import ConfigurationError

    monkeypatch.setenv("OPENROUTER_API_KEY", "short")
    try:
        provider = EnvOpenRouterConfigProvider()
        with (
            pytest.raises(ConfigurationError, match="API Key validation failed"),
            provider.get_api_key(),
        ):
            pass
    finally:
        pass


def test_settings_api_key_invalid_format(
    tmp_path: typing.Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    from src.config import EnvOpenRouterConfigProvider
    from src.domain_models.exceptions import ConfigurationError

    monkeypatch.setenv(
        "OPENROUTER_API_KEY", "invalid_key_with_spaces_too_long_to_pass_length_check"
    )
    try:
        provider = EnvOpenRouterConfigProvider()
        with (
            pytest.raises(ConfigurationError, match="API Key validation failed"),
            provider.get_api_key(),
        ):
            pass
    finally:
        pass
