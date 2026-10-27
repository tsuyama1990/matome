import json
import math
import re
import struct
import subprocess
import wave
import zlib
from pathlib import Path
from typing import Any

import pytest

from src.txt2speech.config import Settings
from src.txt2speech.errors import EngineError
from src.txt2speech.mp3 import check, encode

_FFMPEG_BIN = "/usr/bin/ffmpeg"
_FFPROBE_BIN = "/usr/bin/ffprobe"
_SINE_RATE = 24000
_SINE_DURATION_SECONDS = 20
_SINE_FREQ_HZ = 440.0
_SINE_AMPLITUDE = 3000
_LUFS_TOLERANCE = 1.0
_EBUR128_INTEGRATED_RE = re.compile(r"\bI:\s*(-?\d+(?:\.\d+)?)\s*LUFS")


def _write_low_volume_sine_wav(
    path: Path,
    duration_seconds: int = _SINE_DURATION_SECONDS,
) -> None:
    one_second_samples = [
        int(_SINE_AMPLITUDE * math.sin(2.0 * math.pi * _SINE_FREQ_HZ * i / _SINE_RATE))
        for i in range(_SINE_RATE)
    ]
    one_second_bytes = struct.pack(f"<{_SINE_RATE}h", *one_second_samples)
    with wave.open(str(path), "wb") as writer:
        writer.setnchannels(1)
        writer.setsampwidth(2)
        writer.setframerate(_SINE_RATE)
        writer.writeframes(one_second_bytes * duration_seconds)


def _png_chunk(chunk_type: bytes, data: bytes) -> bytes:
    crc = zlib.crc32(chunk_type + data) & 0xFFFFFFFF
    return struct.pack(">I", len(data)) + chunk_type + data + struct.pack(">I", crc)


def _write_minimal_png(path: Path) -> None:
    signature = b"\x89PNG\r\n\x1a\n"
    ihdr = _png_chunk(b"IHDR", struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0))
    idat = _png_chunk(b"IDAT", zlib.compress(b"\x00\xff\x00\x00"))
    iend = _png_chunk(b"IEND", b"")
    path.write_bytes(signature + ihdr + idat + iend)


def _probe_mp3(path: Path) -> dict[str, Any]:
    cmd = [
        _FFPROBE_BIN,
        "-v",
        "error",
        "-show_format",
        "-show_streams",
        "-of",
        "json",
        str(path),
    ]
    # Static ffprobe command against test file inside tmp_path.
    proc = subprocess.run(cmd, capture_output=True, text=True, check=True)  # noqa: S603
    loaded: dict[str, Any] = json.loads(proc.stdout)
    return loaded


def _measure_integrated_lufs(path: Path) -> float:
    cmd = [
        _FFMPEG_BIN,
        "-nostats",
        "-i",
        str(path),
        "-af",
        "ebur128=peak=true",
        "-f",
        "null",
        "-",
    ]
    # Static ffmpeg ebur128 measurement command against test file inside tmp_path.
    proc = subprocess.run(cmd, capture_output=True, text=True, check=True)  # noqa: S603
    matches = _EBUR128_INTEGRATED_RE.findall(proc.stderr)
    assert matches, f"Failed to parse integrated loudness from stderr: {proc.stderr}"
    return float(matches[-1])


@pytest.mark.requirement("REQ-2026-002-F08")
def test_encode_produces_normalized_mp3_with_expected_tags_and_stream_info(
    tmp_path: Path,
) -> None:
    """T2S-I08: mp3.encode normalizes a 20s low-volume WAV to -16±1.0 LUFS and sets ID3v2.4 tags."""
    wav_path = tmp_path / "input.wav"
    out_mp3 = tmp_path / "01_第1章.mp3"
    _write_low_volume_sine_wav(wav_path)

    settings = Settings(ffmpeg_path=_FFMPEG_BIN)
    encode(
        wav_path=wav_path,
        out_path=out_mp3,
        title="第1章 はじめに",
        album="テスト教科書",
        track=1,
        settings=settings,
    )

    assert out_mp3.is_file()
    probe = _probe_mp3(out_mp3)
    streams = probe["streams"]
    assert len(streams) == 1
    audio_stream = streams[0]
    assert audio_stream["codec_name"] == "mp3"
    assert audio_stream["sample_rate"] == "44100"
    assert audio_stream["channels"] == 1

    stream_bitrate = int(audio_stream.get("bit_rate", probe["format"]["bit_rate"]))
    assert 115000 <= stream_bitrate <= 140000

    raw_tags = probe["format"]["tags"]
    tags = {k.lower(): v for k, v in raw_tags.items()}
    assert tags["title"] == "第1章 はじめに"
    assert tags["artist"] == "VOICEVOX"
    assert tags["album"] == "テスト教科書"
    assert tags["track"] == "1"
    assert tags["genre"] == "Audiobook"

    measured_lufs = _measure_integrated_lufs(out_mp3)
    assert abs(measured_lufs - settings.loudness_lufs) <= _LUFS_TOLERANCE


@pytest.mark.requirement("REQ-2026-002-F08")
def test_encode_with_and_without_cover_image(tmp_path: Path) -> None:
    """T2S-I09: mp3.encode embeds an attached picture stream when cover is set and omits it if None."""
    wav_path = tmp_path / "input.wav"
    _write_low_volume_sine_wav(wav_path, duration_seconds=3)
    cover_path = tmp_path / "cover.png"
    _write_minimal_png(cover_path)

    with_cover_mp3 = tmp_path / "with_cover.mp3"
    encode(
        wav_path=wav_path,
        out_path=with_cover_mp3,
        title="カバーあり",
        album="アルバム",
        track=1,
        settings=Settings(ffmpeg_path=_FFMPEG_BIN, cover=cover_path),
    )
    with_cover_streams = _probe_mp3(with_cover_mp3)["streams"]
    codec_types_with_cover = [s["codec_type"] for s in with_cover_streams]
    assert "audio" in codec_types_with_cover
    assert "video" in codec_types_with_cover
    video_streams = [s for s in with_cover_streams if s["codec_type"] == "video"]
    assert video_streams[0]["disposition"]["attached_pic"] == 1

    without_cover_mp3 = tmp_path / "without_cover.mp3"
    encode(
        wav_path=wav_path,
        out_path=without_cover_mp3,
        title="カバーなし",
        album="アルバム",
        track=2,
        settings=Settings(ffmpeg_path=_FFMPEG_BIN, cover=None),
    )
    without_cover_streams = _probe_mp3(without_cover_mp3)["streams"]
    assert [s["codec_type"] for s in without_cover_streams] == ["audio"]


@pytest.mark.requirement("REQ-2026-002-F08")
def test_check_and_encode_failure_cases(tmp_path: Path) -> None:
    """T2S-I10: mp3.check and encode raise EngineError on missing binary, ffmpeg v4, or broken WAV."""
    check(Settings(ffmpeg_path=_FFMPEG_BIN))

    missing_bin = str(tmp_path / "no_such_ffmpeg")
    with pytest.raises(EngineError) as missing_exc:
        check(Settings(ffmpeg_path=missing_bin))
    assert missing_bin in str(missing_exc.value)

    fake_v4 = tmp_path / "ffmpeg_v4"
    fake_v4.write_text(
        "#!/bin/sh\necho 'ffmpeg version 4.4.2 Copyright (c) 2000-2021 the FFmpeg developers'\n",
        encoding="utf-8",
    )
    fake_v4.chmod(0o755)
    with pytest.raises(EngineError) as v4_exc:
        check(Settings(ffmpeg_path=str(fake_v4)))
    assert "4.4.2" in str(v4_exc.value)

    fake_git = tmp_path / "ffmpeg_git"
    fake_git.write_text(
        "#!/bin/sh\necho 'ffmpeg version N-12345-gabcdef Copyright (c) FFmpeg developers'\n",
        encoding="utf-8",
    )
    fake_git.chmod(0o755)
    check(Settings(ffmpeg_path=str(fake_git)))

    broken_wav = tmp_path / "broken.wav"
    broken_wav.write_bytes(b"not a valid RIFF/WAV file")
    with pytest.raises(EngineError) as broken_exc:
        encode(
            wav_path=broken_wav,
            out_path=tmp_path / "out.mp3",
            title="壊れた音声",
            album="テスト",
            track=1,
            settings=Settings(ffmpeg_path=_FFMPEG_BIN),
        )
    assert str(broken_exc.value)
