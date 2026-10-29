from pathlib import Path

import pytest

from src.summarize.settings import (
    DEFAULT_LLM_COMMAND,
    DEFAULT_LLM_RETRIES,
    DEFAULT_SUMMARY_MIN_CHARS,
    load_summary_settings,
)

_CONFIG_YAML = """
summary_ratio: 0.35
density_rounds: 3
llm_timeout_seconds: 120.0
"""


@pytest.mark.requirement("REQ-2026-003-F08")
def test_sum_i14_load_summary_settings_from_yaml(tmp_path: Path) -> None:
    """SUM-I14: load_summary_settings loads YAML overrides while keeping defaults for omitted fields."""
    config_file = tmp_path / "config.yaml"
    config_file.write_text(_CONFIG_YAML, encoding="utf-8")

    settings = load_summary_settings(config_file)

    assert settings.summary_ratio == 0.35
    assert settings.density_rounds == 3
    assert settings.llm_timeout_seconds == 120.0

    # Omitted fields retain defaults
    assert settings.summary_min_chars == DEFAULT_SUMMARY_MIN_CHARS
    assert settings.llm_retries == DEFAULT_LLM_RETRIES
    assert settings.llm_command == DEFAULT_LLM_COMMAND
