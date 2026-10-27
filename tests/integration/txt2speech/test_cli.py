import io
import wave
from pathlib import Path

import pytest

from src.txt2speech.cli import EXIT_ENGINE_ERROR, EXIT_INPUT_ERROR, EXIT_OK, main
from src.txt2speech.config import load_settings
from src.txt2speech.dictionary import DictEntry
from src.txt2speech.errors import InputError

_WAV_RATE = 24000
_WAV_CHANNELS = 1
_WAV_SAMPWIDTH = 2
_WAV_FRAMES = 240
_UNUSED_LOCAL_URL = "http://127.0.0.1:1"
_EXTERNAL_URL = "http://example.com:50021"


def _make_wav_bytes() -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as writer:
        writer.setnchannels(_WAV_CHANNELS)
        writer.setsampwidth(_WAV_SAMPWIDTH)
        writer.setframerate(_WAV_RATE)
        writer.writeframes(b"\x00\x00" * _WAV_FRAMES)
    return buf.getvalue()


class _StubClient:
    def check(self) -> None:
        return None

    def register(self, _entry: DictEntry) -> None:
        return None

    def synthesize(self, _text: str) -> bytes:
        return _make_wav_bytes()


def _stub_encoder(
    wav_path: Path,
    out_path: Path,
    _title: str,
    _album: str,
    _track: int,
) -> None:
    assert wav_path.is_file()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_bytes(b"FAKE_MP3")


@pytest.mark.requirement("REQ-2026-002-F10")
@pytest.mark.requirement("REQ-2026-002-F11")
def test_load_settings_and_cli_config_validation(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """T2S-I18: load_settings and cli.main apply overrides and reject invalid config inputs."""
    input_path = tmp_path / "book.txt"
    input_path.write_text("テスト本文です。", encoding="utf-8")
    out_dir = tmp_path / "out"
    cover_path = tmp_path / "cover.png"
    cover_path.write_bytes(b"PNG")
    dict_path = tmp_path / "terms.csv"
    dict_path.write_text(
        "surface,pronunciation,accent_type\nCO2,シーオーツー,5\n", encoding="utf-8"
    )

    config_yaml = tmp_path / "config.yaml"
    config_yaml.write_text(
        "speaker: 2\nspeed_scale: 1.1\nvoice_name: YAML_VOICE\nalbum: YAML_ALBUM\n",
        encoding="utf-8",
    )

    merged = load_settings(
        config_yaml,
        {"speaker": 5, "speed_scale": 1.25, "cover": cover_path, "dictionaries": (dict_path,)},
    )
    assert merged.speaker == 5
    assert merged.speed_scale == 1.25
    assert merged.voice_name == "YAML_VOICE"
    assert merged.album == "YAML_ALBUM"
    assert merged.cover == cover_path
    assert merged.dictionaries == (dict_path,)

    # Valid config and CLI overrides pass validation and reach engine check on unused local port.
    code = main(
        [
            str(input_path),
            "-o",
            str(out_dir),
            "--config",
            str(config_yaml),
            "--speaker",
            "4",
            "--speed-scale",
            "1.15",
            "--max-chars",
            "60",
            "--cover",
            str(cover_path),
            "--album",
            "CLI_ALBUM",
            "--voice-name",
            "CLI_VOICE",
            "--dictionary",
            str(dict_path),
            "--engine-url",
            _UNUSED_LOCAL_URL,
        ]
    )
    assert code == EXIT_ENGINE_ERROR
    capsys.readouterr()

    unknown_yaml = tmp_path / "unknown.yaml"
    unknown_yaml.write_text("not_a_setting: true\n", encoding="utf-8")
    with pytest.raises(InputError):
        load_settings(unknown_yaml, {})
    assert (
        main([str(input_path), "-o", str(out_dir), "--config", str(unknown_yaml)])
        == EXIT_INPUT_ERROR
    )

    with pytest.raises(InputError):
        load_settings(None, {"speed_scale": 2.5})
    assert main([str(input_path), "-o", str(out_dir), "--speed-scale", "2.5"]) == EXIT_INPUT_ERROR

    with pytest.raises(InputError):
        load_settings(None, {"engine_url": _EXTERNAL_URL})
    assert (
        main([str(input_path), "-o", str(out_dir), "--engine-url", _EXTERNAL_URL])
        == EXIT_INPUT_ERROR
    )

    missing_cover = tmp_path / "missing_cover.png"
    with pytest.raises(InputError):
        load_settings(None, {"cover": missing_cover})
    assert (
        main([str(input_path), "-o", str(out_dir), "--cover", str(missing_cover)])
        == EXIT_INPUT_ERROR
    )
    capsys.readouterr()


@pytest.mark.requirement("REQ-2026-002-F10")
@pytest.mark.requirement("REQ-2026-002-F11")
def test_cli_main_exit_codes_for_error_conditions(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """T2S-I19: cli.main returns 2, 2, 3, 2, 3 for arg, input, engine, host, and ffmpeg errors."""
    input_path = tmp_path / "input.txt"
    input_path.write_text("第1章 はじめに\n本文です。\n", encoding="utf-8")
    out_dir = tmp_path / "out"

    code_arg_err = main([str(input_path)])
    captured_arg = capsys.readouterr()
    assert code_arg_err == EXIT_INPUT_ERROR
    assert captured_arg.out == ""
    assert captured_arg.err != ""

    code_missing_input = main([str(tmp_path / "no_such_input.txt"), "-o", str(out_dir)])
    captured_missing = capsys.readouterr()
    assert code_missing_input == EXIT_INPUT_ERROR
    assert captured_missing.out == ""
    assert captured_missing.err != ""

    code_engine_down = main(
        [str(input_path), "-o", str(out_dir), "--engine-url", _UNUSED_LOCAL_URL]
    )
    captured_engine = capsys.readouterr()
    assert code_engine_down == EXIT_ENGINE_ERROR
    assert captured_engine.out == ""
    assert _UNUSED_LOCAL_URL in captured_engine.err

    code_external_url = main([str(input_path), "-o", str(out_dir), "--engine-url", _EXTERNAL_URL])
    captured_external = capsys.readouterr()
    assert code_external_url == EXIT_INPUT_ERROR
    assert captured_external.out == ""
    assert _EXTERNAL_URL in captured_external.err

    missing_ffmpeg = str(tmp_path / "no_such_ffmpeg")
    code_no_ffmpeg = main([str(input_path), "-o", str(out_dir), "--ffmpeg", missing_ffmpeg])
    captured_ffmpeg = capsys.readouterr()
    assert code_no_ffmpeg == EXIT_ENGINE_ERROR
    assert captured_ffmpeg.out == ""
    assert missing_ffmpeg in captured_ffmpeg.err

    assert [
        code_arg_err,
        code_missing_input,
        code_engine_down,
        code_external_url,
        code_no_ffmpeg,
    ] == [2, 2, 3, 2, 3]


@pytest.mark.requirement("REQ-2026-002-F10")
def test_cli_main_progress_on_stderr_and_mp3_paths_on_stdout(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """T2S-I20: cli.main writes tqdm progress to stderr and only MP3 file paths to stdout."""
    input_path = tmp_path / "textbook.md"
    input_path.write_text(
        "# 第1章 序論\n序論の一文目です。序論の二文目です。\n\n# 第2章 結論\n結論の文です。\n",
        encoding="utf-8",
    )
    out_dir = tmp_path / "out"

    exit_code = main(
        [str(input_path), "-o", str(out_dir)],
        client=_StubClient(),
        encoder=_stub_encoder,
    )
    captured = capsys.readouterr()

    assert exit_code == EXIT_OK
    expected_paths = [
        str(out_dir / "01_第1章 序論.mp3"),
        str(out_dir / "02_第2章 結論.mp3"),
    ]
    assert captured.out.splitlines() == expected_paths
    assert "章 1/2" in captured.err
    assert "章 2/2" in captured.err
