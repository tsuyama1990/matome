import json
import re
import subprocess
from pathlib import Path

from src.txt2speech.config import Settings
from src.txt2speech.errors import EngineError

_MIN_FFMPEG_MAJOR_VERSION = 5
_MONO_CHANNELS = "1"
_AUDIO_CODEC = "libmp3lame"
_ID3V2_VERSION = "4"

_VERSION_LINE_RE = re.compile(r"^ffmpeg version (\S+)")
_LEADING_DIGITS_RE = re.compile(r"^(\d+)")
_JSON_BLOCK_RE = re.compile(r"\{[^{}]*\}", re.DOTALL)

_LOUDNORM_PASS1_TEMPLATE = "loudnorm=I={i}:TP={tp}:LRA={lra}:print_format=json"
_LOUDNORM_PASS2_TEMPLATE = (
    "loudnorm=I={i}:TP={tp}:LRA={lra}"
    ":measured_I={measured_i}"
    ":measured_TP={measured_tp}"
    ":measured_LRA={measured_lra}"
    ":measured_thresh={measured_thresh}"
    ":offset={offset}"
    ":linear=true"
)
_LOUDNORM_REQUIRED_KEYS: tuple[str, ...] = (
    "input_i",
    "input_tp",
    "input_lra",
    "input_thresh",
    "target_offset",
)


def _missing_ffmpeg_message(ffmpeg_path: str) -> str:
    return (
        f"ffmpeg が見つかりません: {ffmpeg_path}。"
        f"FFmpeg {_MIN_FFMPEG_MAJOR_VERSION} 以上をインストールして PATH に通すか、"
        "--ffmpeg で指定してください"
    )


def _run_ffmpeg(cmd: list[str], ffmpeg_path: str) -> subprocess.CompletedProcess[str]:
    try:
        # Arguments are passed as a list without shell=True; binary path is configured via Settings.
        result = subprocess.run(  # noqa: S603
            cmd,
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError as exc:
        msg = _missing_ffmpeg_message(ffmpeg_path)
        raise EngineError(msg) from exc
    return result


def check(settings: Settings) -> None:
    result = _run_ffmpeg([settings.ffmpeg_path, "-version"], settings.ffmpeg_path)
    if result.returncode != 0:
        msg = _missing_ffmpeg_message(settings.ffmpeg_path)
        raise EngineError(msg)

    lines = result.stdout.splitlines()
    first_line = lines[0] if lines else ""
    version_match = _VERSION_LINE_RE.match(first_line)
    if version_match is None:
        return

    version_str = version_match.group(1)
    major_match = _LEADING_DIGITS_RE.match(version_str)
    # Non-numeric development builds (e.g. N-12345-g...) are allowed through.
    if major_match is None:
        return

    major_version = int(major_match.group(1))
    if major_version < _MIN_FFMPEG_MAJOR_VERSION:
        msg = (
            f"ffmpeg のバージョンが古すぎます (version {version_str}): {settings.ffmpeg_path}。"
            f"FFmpeg {_MIN_FFMPEG_MAJOR_VERSION} 以上をインストールして PATH に通すか、"
            "--ffmpeg で指定してください"
        )
        raise EngineError(msg)


def _parse_loudnorm_json(stderr: str) -> dict[str, str]:
    blocks = _JSON_BLOCK_RE.findall(stderr)
    if not blocks:
        msg = f"ffmpeg loudnorm の測定 JSON が見つかりません: {stderr}"
        raise EngineError(msg)

    try:
        parsed = json.loads(blocks[-1])
    except json.JSONDecodeError as exc:
        msg = f"ffmpeg loudnorm の測定 JSON の解析に失敗しました: {stderr}"
        raise EngineError(msg) from exc

    if not isinstance(parsed, dict):
        msg = f"ffmpeg loudnorm の測定結果がオブジェクトではありません: {stderr}"
        raise EngineError(msg)

    measurements: dict[str, str] = {}
    for key in _LOUDNORM_REQUIRED_KEYS:
        if key not in parsed:
            msg = f"ffmpeg loudnorm の測定結果に {key} がありません: {stderr}"
            raise EngineError(msg)
        measurements[key] = str(parsed[key])
    return measurements


def _measure_loudness(wav_path: Path, settings: Settings) -> dict[str, str]:
    pass1_filter = _LOUDNORM_PASS1_TEMPLATE.format(
        i=settings.loudness_lufs,
        tp=settings.true_peak_dbfs,
        lra=settings.loudness_range,
    )
    cmd = [
        settings.ffmpeg_path,
        "-hide_banner",
        "-nostats",
        "-i",
        str(wav_path),
        "-af",
        pass1_filter,
        "-f",
        "null",
        "-",
    ]
    result = _run_ffmpeg(cmd, settings.ffmpeg_path)
    if result.returncode != 0:
        msg = f"ffmpeg ラウドネス測定に失敗しました: {result.stderr}"
        raise EngineError(msg)
    return _parse_loudnorm_json(result.stderr)


def _build_encode_command(
    wav_path: Path,
    out_path: Path,
    title: str,
    album: str,
    track: int | str,
    measurements: dict[str, str],
    settings: Settings,
) -> list[str]:
    pass2_filter = _LOUDNORM_PASS2_TEMPLATE.format(
        i=settings.loudness_lufs,
        tp=settings.true_peak_dbfs,
        lra=settings.loudness_range,
        measured_i=measurements["input_i"],
        measured_tp=measurements["input_tp"],
        measured_lra=measurements["input_lra"],
        measured_thresh=measurements["input_thresh"],
        offset=measurements["target_offset"],
    )
    cmd = [
        settings.ffmpeg_path,
        "-y",
        "-hide_banner",
        "-loglevel",
        "error",
        "-i",
        str(wav_path),
    ]
    if settings.cover is not None:
        cmd.extend(["-i", str(settings.cover)])
    cmd.extend(["-map", "0:a"])
    if settings.cover is not None:
        cmd.extend(["-map", "1:v", "-c:v", "copy", "-disposition:v:0", "attached_pic"])
    cmd.extend(
        [
            "-af",
            pass2_filter,
            "-ar",
            str(settings.sample_rate_hz),
            "-ac",
            _MONO_CHANNELS,
            "-codec:a",
            _AUDIO_CODEC,
            "-b:a",
            settings.bitrate,
            "-id3v2_version",
            _ID3V2_VERSION,
            "-metadata",
            f"title={title}",
            "-metadata",
            f"artist={settings.voice_name}",
            "-metadata",
            f"album={album}",
            "-metadata",
            f"track={track}",
            "-metadata",
            f"genre={settings.genre}",
            str(out_path),
        ]
    )
    return cmd


def encode(
    wav_path: Path,
    out_path: Path,
    title: str,
    album: str,
    track: int | str,
    settings: Settings,
) -> None:
    measurements = _measure_loudness(wav_path, settings)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = _build_encode_command(wav_path, out_path, title, album, track, measurements, settings)
    result = _run_ffmpeg(cmd, settings.ffmpeg_path)
    if result.returncode != 0:
        msg = f"ffmpeg MP3 変換に失敗しました: {result.stderr}"
        raise EngineError(msg)
