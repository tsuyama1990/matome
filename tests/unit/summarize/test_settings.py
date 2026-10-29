import pytest

from src.summarize.settings import (
    DEFAULT_DENSITY_ROUNDS,
    DEFAULT_LLM_COMMAND,
    DEFAULT_LLM_RETRIES,
    DEFAULT_LLM_RETRY_WAIT_SECONDS,
    DEFAULT_LLM_TIMEOUT_SECONDS,
    DEFAULT_MAX_PROMPT_BYTES,
    DEFAULT_SUMMARY_MIN_CHARS,
    DEFAULT_SUMMARY_RATIO,
    load_summary_settings,
)
from src.txt2speech.errors import InputError


@pytest.mark.requirement("REQ-2026-003-F08")
@pytest.mark.parametrize(
    ("key", "invalid_value"),
    [
        ("summary_ratio", 0),
        ("summary_ratio", 1.1),
        ("summary_min_chars", 0),
        ("density_rounds", -1),
        ("llm_retries", -1),
        ("llm_retry_wait_seconds", 0),
        ("llm_timeout_seconds", 0),
        ("max_prompt_bytes", 0),
    ],
)
def test_sum_u10_validate_numeric_settings_rejects_out_of_bounds(
    key: str,
    invalid_value: object,
) -> None:
    """SUM-U10: settings validation raises InputError mentioning key for out-of-range values."""
    with pytest.raises(InputError, match=key):
        load_summary_settings(overrides={key: invalid_value})


@pytest.mark.requirement("REQ-2026-003-F08")
@pytest.mark.parametrize(
    "invalid_command",
    [
        [],
        "agy-cli",
        [""],
    ],
)
def test_sum_u11_validate_llm_command_requires_non_empty_sequence_of_strings(
    invalid_command: object,
) -> None:
    """SUM-U11: settings validation raises InputError for invalid llm_command structures."""
    with pytest.raises(InputError, match="llm_command"):
        load_summary_settings(overrides={"llm_command": invalid_command})


@pytest.mark.requirement("REQ-2026-003-F08")
def test_sum_u12_validate_rejects_unknown_keys_and_invalid_chapter_spec() -> None:
    """SUM-U12: settings validation raises InputError for unknown keys and invalid chapter range."""
    with pytest.raises(InputError, match="未知の設定キー"):
        load_summary_settings(overrides={"unexpected_option": "value"})

    with pytest.raises(InputError):
        load_summary_settings(overrides={"chapters": "5-2"})


@pytest.mark.requirement("REQ-2026-003-F02")
@pytest.mark.requirement("REQ-2026-003-F08")
def test_sum_u13_default_summary_settings_match_specification() -> None:
    """SUM-U13: default SummarySettings match specification defaults."""
    settings = load_summary_settings()

    assert settings.summary_ratio == DEFAULT_SUMMARY_RATIO
    assert settings.summary_ratio == 0.2
    assert settings.summary_min_chars == DEFAULT_SUMMARY_MIN_CHARS
    assert settings.summary_min_chars == 300
    assert settings.density_rounds == DEFAULT_DENSITY_ROUNDS
    assert settings.density_rounds == 1
    assert settings.llm_retries == DEFAULT_LLM_RETRIES
    assert settings.llm_retries == 2
    assert settings.llm_retry_wait_seconds == DEFAULT_LLM_RETRY_WAIT_SECONDS
    assert settings.llm_retry_wait_seconds == 2.0
    assert settings.llm_timeout_seconds == DEFAULT_LLM_TIMEOUT_SECONDS
    assert settings.llm_timeout_seconds == 900.0
    assert settings.max_prompt_bytes == DEFAULT_MAX_PROMPT_BYTES
    assert settings.max_prompt_bytes == 100_000
    assert settings.llm_command == DEFAULT_LLM_COMMAND
    assert settings.llm_command == (
        "agy-cli",
        "--model",
        "Gemini 4 Argon (High)",
        "--print-timeout",
        "600s",
        "-p",
    )
    assert settings.chapters is None
