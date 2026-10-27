import io
import wave
from collections.abc import Sequence
from pathlib import Path

from src.txt2speech.config import Settings
from src.txt2speech.errors import EngineError
from src.txt2speech.models import Boundary

_MS_PER_SECOND = 1000
_WavFormat = tuple[int, int, int]


def pause_frames(boundary: Boundary, settings: Settings, rate: int) -> int:
    return settings.pause_ms[boundary] * rate // _MS_PER_SECOND


def write_wav(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


def _read_wav_stream(stream: io.BytesIO | str, label: str) -> tuple[_WavFormat, bytes]:
    try:
        with wave.open(stream, "rb") as reader:
            fmt: _WavFormat = (
                reader.getnchannels(),
                reader.getsampwidth(),
                reader.getframerate(),
            )
            frames = reader.readframes(reader.getnframes())
    except (wave.Error, EOFError, OSError) as exc:
        msg = f"WAV の読み込みに失敗しました: {label}"
        raise EngineError(msg) from exc
    return fmt, frames


def _configure_or_verify_format(
    writer: wave.Wave_write,
    expected_fmt: _WavFormat | None,
    current_fmt: _WavFormat,
) -> _WavFormat:
    if expected_fmt is None:
        nchannels, sampwidth, framerate = current_fmt
        writer.setnchannels(nchannels)
        writer.setsampwidth(sampwidth)
        writer.setframerate(framerate)
        return current_fmt
    if current_fmt != expected_fmt:
        msg = f"WAV の形式が一致しません: {current_fmt} != {expected_fmt}"
        raise EngineError(msg)
    return expected_fmt


def concat_wav_bytes(parts: Sequence[bytes]) -> bytes:
    if not parts:
        msg = "連結する WAV データが空です"
        raise EngineError(msg)

    out_buf = io.BytesIO()
    expected_fmt: _WavFormat | None = None
    with wave.open(out_buf, "wb") as writer:
        for index, raw in enumerate(parts):
            fmt, frames = _read_wav_stream(io.BytesIO(raw), f"part[{index}]")
            expected_fmt = _configure_or_verify_format(writer, expected_fmt, fmt)
            writer.writeframes(frames)

    return out_buf.getvalue()


def join_wav_files(
    paths: Sequence[Path],
    boundaries: Sequence[Boundary],
    settings: Settings,
    out_path: Path,
) -> None:
    if not paths:
        msg = "結合する WAV ファイルが指定されていません"
        raise EngineError(msg)
    if len(paths) != len(boundaries):
        msg = "paths と boundaries の要素数が一致しません"
        raise EngineError(msg)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    expected_fmt: _WavFormat | None = None
    last_index = len(paths) - 1

    try:
        with wave.open(str(out_path), "wb") as writer:
            for index, (wav_path, boundary) in enumerate(zip(paths, boundaries, strict=True)):
                # Read one WAV file at a time so the full chapter audio is never held in memory.
                fmt, frames = _read_wav_stream(str(wav_path), str(wav_path))
                expected_fmt = _configure_or_verify_format(writer, expected_fmt, fmt)
                writer.writeframes(frames)

                if index < last_index:
                    nchannels, sampwidth, framerate = expected_fmt
                    silence_frames = pause_frames(boundary, settings, framerate)
                    silence_bytes = b"\x00" * (silence_frames * nchannels * sampwidth)
                    writer.writeframes(silence_bytes)
    except (wave.Error, OSError) as exc:
        msg = f"WAV ファイルの書き出しに失敗しました: {out_path}"
        raise EngineError(msg) from exc
