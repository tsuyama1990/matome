import io
import wave
from pathlib import Path
from typing import Any

import pytest

from src.txt2speech.audio import concat_wav_bytes, join_wav_files, pause_frames, write_wav
from src.txt2speech.config import Settings
from src.txt2speech.errors import EngineError, InputError
from src.txt2speech.models import Boundary
from src.txt2speech.progress import Progress
from src.txt2speech.text_io import read_text

_RATE_24K = 24000
_RATE_44K = 44100


def _make_wav_bytes(
    n_frames: int,
    rate: int = _RATE_24K,
    channels: int = 1,
    sampwidth: int = 2,
) -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as writer:
        writer.setnchannels(channels)
        writer.setsampwidth(sampwidth)
        writer.setframerate(rate)
        writer.writeframes(b"\x01\x00" * (n_frames * channels))
    return buf.getvalue()


@pytest.mark.requirement("REQ-2026-002-F07")
def test_join_wav_files_frame_count_and_format_mismatch(tmp_path: Path) -> None:
    """T2S-I11: join_wav_files inserts boundary pauses between files and rejects format mismatches."""
    settings = Settings()
    wav1 = tmp_path / "0001.wav"
    wav2 = tmp_path / "0002.wav"
    wav3 = tmp_path / "0003.wav"
    write_wav(wav1, _make_wav_bytes(1000))
    write_wav(wav2, _make_wav_bytes(2000))
    write_wav(wav3, _make_wav_bytes(1500))

    boundaries: list[Boundary] = ["comma", "sentence", "paragraph"]
    out_wav = tmp_path / "joined.wav"
    join_wav_files([wav1, wav2, wav3], boundaries, settings, out_wav)

    expected_frames = (
        1000
        + pause_frames("comma", settings, _RATE_24K)
        + 2000
        + pause_frames("sentence", settings, _RATE_24K)
        + 1500
    )
    with wave.open(str(out_wav), "rb") as reader:
        assert reader.getnframes() == expected_frames
        assert reader.getframerate() == _RATE_24K
        assert reader.getnchannels() == 1

    # Verify concat_wav_bytes joins without pause and checks format consistency.
    concatenated = concat_wav_bytes([_make_wav_bytes(1000), _make_wav_bytes(2000)])
    with wave.open(io.BytesIO(concatenated), "rb") as reader:
        assert reader.getnframes() == 3000

    with pytest.raises(EngineError):
        concat_wav_bytes(
            [
                _make_wav_bytes(1000, rate=_RATE_24K),
                _make_wav_bytes(1000, rate=_RATE_44K),
            ]
        )

    mismatched_wav = tmp_path / "mismatch.wav"
    write_wav(mismatched_wav, _make_wav_bytes(1000, rate=_RATE_44K))
    with pytest.raises(EngineError):
        join_wav_files(
            [wav1, mismatched_wav],
            ["comma", "paragraph"],
            settings,
            tmp_path / "failed.wav",
        )


@pytest.mark.requirement("REQ-2026-002-F07")
def test_join_wav_files_reads_one_file_at_a_time(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """T2S-I11: join_wav_files reads input WAV files sequentially one at a time."""
    paths: list[Path] = []
    for idx, frame_count in enumerate((800, 1200, 600), start=1):
        wav_path = tmp_path / f"{idx:04d}.wav"
        write_wav(wav_path, _make_wav_bytes(frame_count))
        paths.append(wav_path)

    original_wave_open = wave.open
    active_readers = 0
    max_concurrent_readers = 0
    read_order: list[str] = []

    class _TrackedReader:
        def __init__(self, inner: wave.Wave_read) -> None:
            self._inner = inner

        def __enter__(self) -> wave.Wave_read:
            return self._inner

        def __exit__(self, *args: object) -> None:
            nonlocal active_readers
            active_readers -= 1
            self._inner.close()

    def tracked_wave_open(f: Any, mode: str | None = None) -> Any:
        nonlocal active_readers, max_concurrent_readers
        raw_obj = original_wave_open(f, mode)
        if mode == "rb":
            active_readers += 1
            max_concurrent_readers = max(max_concurrent_readers, active_readers)
            if isinstance(f, str):
                read_order.append(Path(f).name)
            return _TrackedReader(raw_obj)
        return raw_obj

    monkeypatch.setattr(wave, "open", tracked_wave_open)

    settings = Settings()
    out_wav = tmp_path / "sequential.wav"
    join_wav_files(paths, ["other", "comma", "paragraph"], settings, out_wav)

    assert max_concurrent_readers == 1
    assert read_order == ["0001.wav", "0002.wav", "0003.wav"]


@pytest.mark.requirement("REQ-2026-002-F01")
def test_read_text_encodings_and_error_cases(tmp_path: Path) -> None:
    """T2S-I12: read_text reads UTF-8, UTF-8 with BOM, and CP932 identically and rejects bad inputs."""
    expected = "教科書のテキストを音声化するテスト。\n第1章 序論"

    utf8_file = tmp_path / "utf8.txt"
    utf8_file.write_bytes(expected.encode("utf-8"))

    utf8_bom_file = tmp_path / "utf8_bom.txt"
    utf8_bom_file.write_bytes(expected.encode("utf-8-sig"))

    cp932_file = tmp_path / "cp932.txt"
    cp932_file.write_bytes(expected.encode("cp932"))

    assert read_text(utf8_file) == expected
    assert read_text(utf8_bom_file) == expected
    assert read_text(cp932_file) == expected

    # A CP932 lead byte followed by an ASCII byte is invalid in both UTF-8 and CP932.
    invalid_file = tmp_path / "invalid.txt"
    invalid_file.write_bytes(b"\x81\x20")
    with pytest.raises(InputError) as invalid_exc:
        read_text(invalid_file)
    assert invalid_file.name in str(invalid_exc.value)

    missing_file = tmp_path / "missing.txt"
    with pytest.raises(InputError) as missing_exc:
        read_text(missing_file)
    assert missing_file.name in str(missing_exc.value)


@pytest.mark.requirement("REQ-2026-002-F09")
def test_progress_fingerprint_change_resets_state_and_work_dir(tmp_path: Path) -> None:
    """T2S-I17: Progress.load resets state and clears work_dir contents when fingerprint changes."""
    progress_path = tmp_path / ".txt2speech_progress.json"
    work_dir = tmp_path / ".txt2speech_work"
    stale_chunk = work_dir / "ch01" / "0001.wav"
    stale_chunk.parent.mkdir(parents=True, exist_ok=True)
    stale_chunk.write_bytes(b"wav")

    initial = Progress(progress_path, work_dir, "fp_old")
    initial.mark_chapter_done(1)

    changed = Progress(progress_path, work_dir, "fp_new")
    state = changed.load()
    assert state.done_chapters == []
    assert list(work_dir.iterdir()) == []
