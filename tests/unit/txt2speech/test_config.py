from pathlib import Path

import pytest

from src.txt2speech.config import DEFAULT_BITRATE, load_settings
from src.txt2speech.errors import InputError


@pytest.mark.requirement("REQ-2026-002-F10")
@pytest.mark.requirement("REQ-2026-002-F11")
def test_load_settings_validation_and_loopback(tmp_path: Path) -> None:
    """T2S-U20: load_settings validates YAML keys, ranges, pause keys, files, and loopback URLs."""
    cover_file = tmp_path / "cover.jpg"
    cover_file.write_bytes(b"jpg")
    dict_file = tmp_path / "terms.csv"
    dict_file.write_text("surface,pronunciation,accent_type\n", encoding="utf-8")

    valid_yaml = tmp_path / "valid.yaml"
    valid_yaml.write_text(
        f"speaker: 3\nspeed_scale: 1.15\ncover: {cover_file}\ndictionaries:\n  - {dict_file}\n",
        encoding="utf-8",
    )
    settings = load_settings(valid_yaml, {})
    assert settings.speaker == 3
    assert settings.speed_scale == 1.15
    assert settings.cover == cover_file
    assert settings.dictionaries == (dict_file,)

    unknown_key_yaml = tmp_path / "unknown.yaml"
    unknown_key_yaml.write_text("unknown_option: 123\n", encoding="utf-8")
    with pytest.raises(InputError):
        load_settings(unknown_key_yaml, {})

    with pytest.raises(InputError):
        load_settings(None, {"speed_scale": 3.0})

    with pytest.raises(InputError):
        load_settings(None, {"max_chunk_chars": 3, "min_chunk_chars": 4})

    with pytest.raises(InputError):
        load_settings(None, {"pause_ms": {"paragraph": 900}})

    with pytest.raises(InputError):
        load_settings(None, {"engine_url": "http://example.com:50021"})

    localhost_settings = load_settings(None, {"engine_url": "http://localhost:50021"})
    assert localhost_settings.engine_url == "http://localhost:50021"

    ipv6_settings = load_settings(None, {"engine_url": "http://[::1]:50021"})
    assert ipv6_settings.engine_url == "http://[::1]:50021"


@pytest.mark.requirement("REQ-2026-002-F10")
def test_load_settings_missing_files_and_retries(tmp_path: Path) -> None:
    """T2S-U20: load_settings rejects missing config, cover, or dictionary files and retries < 0."""
    missing_config = tmp_path / "missing.yaml"
    with pytest.raises(InputError):
        load_settings(missing_config, {})

    with pytest.raises(InputError):
        load_settings(None, {"cover": tmp_path / "no_cover.png"})

    with pytest.raises(InputError):
        load_settings(None, {"dictionaries": [tmp_path / "no_dict.csv"]})

    with pytest.raises(InputError):
        load_settings(None, {"retries": -1})


@pytest.mark.requirement("REQ-2026-002-F10")
def test_load_settings_precedence(tmp_path: Path) -> None:
    """T2S-U21: load_settings applies precedence defaults < YAML < overrides."""
    config_yaml = tmp_path / "config.yaml"
    config_yaml.write_text(
        "speaker: 2\nspeed_scale: 1.2\nvoice_name: YAML_VOICE\n",
        encoding="utf-8",
    )

    settings = load_settings(
        config_yaml,
        {"speed_scale": 1.5, "voice_name": "CLI_VOICE"},
    )
    assert settings.bitrate == DEFAULT_BITRATE
    assert settings.speaker == 2
    assert settings.speed_scale == 1.5
    assert settings.voice_name == "CLI_VOICE"
