import io
import wave
from dataclasses import dataclass
from pathlib import Path

import pytest

from src.txt2speech.config import Settings
from src.txt2speech.dictionary import DictEntry
from src.txt2speech.errors import EngineError, InputError, ResourceExhausted
from src.txt2speech.pipeline import run, synthesize_with_halving
from src.txt2speech.progress import Progress, fingerprint

_WAV_RATE = 24000
_WAV_CHANNELS = 1
_WAV_SAMPWIDTH = 2
_FRAMES_PER_CHAR = 100


def _make_wav_bytes(num_frames: int = 240) -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as writer:
        writer.setnchannels(_WAV_CHANNELS)
        writer.setsampwidth(_WAV_SAMPWIDTH)
        writer.setframerate(_WAV_RATE)
        writer.writeframes(b"\x00\x00" * num_frames)
    return buf.getvalue()


@dataclass(frozen=True)
class _EncodeRecord:
    wav_path: Path
    out_path: Path
    title: str
    album: str
    track: int


class _FakeEncoder:
    def __init__(self) -> None:
        self.calls: list[_EncodeRecord] = []

    def __call__(
        self,
        wav_path: Path,
        out_path: Path,
        title: str,
        album: str,
        track: int,
    ) -> None:
        assert wav_path.is_file()
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_bytes(b"FAKE_MP3_DATA")
        self.calls.append(
            _EncodeRecord(
                wav_path=wav_path,
                out_path=out_path,
                title=title,
                album=album,
                track=track,
            )
        )


class _FakeClient:
    def __init__(
        self,
        *,
        fail_check: bool = False,
        exhaust_above_chars: int | None = None,
        crash_on_call: int | None = None,
    ) -> None:
        self.fail_check = fail_check
        self.exhaust_above_chars = exhaust_above_chars
        self.crash_on_call = crash_on_call
        self.check_calls = 0
        self.registered: list[DictEntry] = []
        self.attempted_texts: list[str] = []
        self.synthesized_texts: list[str] = []
        self._in_flight = 0
        self.max_concurrent = 0

    def check(self) -> None:
        self.check_calls += 1
        if self.fail_check:
            msg = "VOICEVOX Engine に接続できません: http://127.0.0.1:50021"
            raise EngineError(msg)

    def register(self, entry: DictEntry) -> None:
        self.registered.append(entry)

    def synthesize(self, text: str) -> bytes:
        self._in_flight += 1
        self.max_concurrent = max(self.max_concurrent, self._in_flight)
        try:
            self.attempted_texts.append(text)
            call_no = len(self.attempted_texts)
            if self.crash_on_call is not None and call_no == self.crash_on_call:
                msg = f"simulated synthesis crash on call {call_no}"
                raise EngineError(msg)
            if self.exhaust_above_chars is not None and len(text) > self.exhaust_above_chars:
                msg = f"resource exhausted for length {len(text)}"
                raise ResourceExhausted(msg)
            self.synthesized_texts.append(text)
            return _make_wav_bytes(max(1, len(text)) * _FRAMES_PER_CHAR)
        finally:
            self._in_flight -= 1


@pytest.mark.requirement("REQ-2026-002-F04")
@pytest.mark.requirement("REQ-2026-002-F09")
def test_pipeline_two_chapters_progress_and_cleanup(tmp_path: Path) -> None:
    """T2S-I13: pipeline.run encodes 01_.../02_... MP3s, notifies progress, and cleans temp files."""
    input_path = tmp_path / "textbook.md"
    input_path.write_text(
        "# 第1章 序論\n最初の段落です。二文目です。\n\n# 第2章 本論\n本論の最初の文です。\n",
        encoding="utf-8",
    )
    out_dir = tmp_path / "out"
    settings = Settings(max_chunk_chars=80)
    client = _FakeClient()
    encoder = _FakeEncoder()
    progress_events: list[tuple[int, int, int, int]] = []

    mp3_paths = run(
        input_path=input_path,
        out_dir=out_dir,
        settings=settings,
        client=client,
        encoder=encoder,
        progress_cb=lambda ch, total_ch, done_ck, total_ck: progress_events.append(
            (ch, total_ch, done_ck, total_ck)
        ),
    )

    assert [p.name for p in mp3_paths] == ["01_第1章 序論.mp3", "02_第2章 本論.mp3"]
    assert all(p.is_file() for p in mp3_paths)
    assert len(encoder.calls) == 2
    assert encoder.calls[0].title == "第1章 序論"
    assert encoder.calls[0].album == "textbook"
    assert encoder.calls[0].track == 1
    assert encoder.calls[1].title == "第2章 本論"
    assert encoder.calls[1].album == "textbook"
    assert encoder.calls[1].track == 2

    assert progress_events == [
        (1, 2, 1, 2),
        (1, 2, 2, 2),
        (2, 2, 1, 1),
    ]
    assert not (out_dir / settings.work_dir_name).exists()
    assert not (out_dir / settings.progress_file_name).exists()


@pytest.mark.requirement("REQ-2026-002-F02")
@pytest.mark.requirement("REQ-2026-002-F05")
@pytest.mark.requirement("REQ-2026-002-F06")
def test_pipeline_sends_preprocessed_bounded_chunks_sequentially(tmp_path: Path) -> None:
    """T2S-I14: pipeline.run sends normalized chunks within max_chunk_chars one at a time."""
    input_path = tmp_path / "science.md"
    input_path.write_text(
        "# 第1章 化学\n"
        "漢字《かんじ》とCO2の濃度は1,000ppmです。図1-1を参照してください。\n"
        "--- 12 ページ ---\n"
        "さらに長い説明が続き、読点で区切られた文が順番に処理されていきます。\n",
        encoding="utf-8",
    )
    out_dir = tmp_path / "out"
    max_chars = 20
    settings = Settings(max_chunk_chars=max_chars)
    client = _FakeClient()
    encoder = _FakeEncoder()

    run(
        input_path=input_path,
        out_dir=out_dir,
        settings=settings,
        client=client,
        encoder=encoder,
    )

    assert len(client.synthesized_texts) >= 2
    assert client.max_concurrent == 1
    for text in client.synthesized_texts:
        assert 1 <= len(text) <= max_chars
        assert "《" not in text
        assert "CO2" not in text
        assert "1,000" not in text
        assert "図1-1" not in text
        assert "ページ" not in text

    combined = "".join(client.synthesized_texts)
    assert "かんじ" in combined
    assert "シーオーツー" in combined
    assert "1000" in combined


@pytest.mark.requirement("REQ-2026-002-F06")
def test_pipeline_halves_on_resource_exhausted_and_fails_when_unsplittable(
    tmp_path: Path,
) -> None:
    """T2S-I15: pipeline.run halves chunks on ResourceExhausted and fails when unsplittable."""
    original_sentence = "これはメモリ不足を模擬するための少し長めのテスト文です。"
    input_path = tmp_path / "long.txt"
    input_path.write_text(original_sentence, encoding="utf-8")
    out_dir = tmp_path / "out"

    settings = Settings(max_chunk_chars=80, min_chunk_chars=4)
    client = _FakeClient(exhaust_above_chars=10)
    encoder = _FakeEncoder()

    mp3_paths = run(
        input_path=input_path,
        out_dir=out_dir,
        settings=settings,
        client=client,
        encoder=encoder,
    )

    assert len(mp3_paths) == 1
    assert len(client.synthesized_texts) >= 3
    assert all(len(part) <= 10 for part in client.synthesized_texts)
    assert "".join(client.synthesized_texts) == original_sentence

    unhalvable_client = _FakeClient(exhaust_above_chars=0)
    with pytest.raises(EngineError) as exc_info:
        synthesize_with_halving("あいうえお", unhalvable_client, min_chars=4)
    assert not isinstance(exc_info.value, ResourceExhausted)


@pytest.mark.requirement("REQ-2026-002-F09")
def test_pipeline_resumes_after_chapter_two_crash_without_resynthesizing(
    tmp_path: Path,
) -> None:
    """T2S-I16: pipeline.run skips finished chapter 1 and existing chapter 2 chunk WAVs on resume."""
    input_path = tmp_path / "resume.md"
    input_path.write_text(
        "# 第1章\n一章の一文目。一章の二文目。\n\n# 第2章\n二章の一文目。二章の二文目。\n",
        encoding="utf-8",
    )
    out_dir = tmp_path / "out"
    settings = Settings(max_chunk_chars=80)

    # Crash on the 4th synthesize call in chapter 2 chunk 2 after chapter 1 finishes.
    crashing_client = _FakeClient(crash_on_call=4)
    encoder_first = _FakeEncoder()
    with pytest.raises(EngineError):
        run(
            input_path=input_path,
            out_dir=out_dir,
            settings=settings,
            client=crashing_client,
            encoder=encoder_first,
        )

    assert crashing_client.synthesized_texts == [
        "一章の一文目。",
        "一章の二文目。",
        "二章の一文目。",
    ]
    assert (out_dir / "01_第1章.mp3").is_file()
    assert not (out_dir / "02_第2章.mp3").exists()
    assert (out_dir / settings.progress_file_name).is_file()
    assert (out_dir / settings.work_dir_name / "ch02" / "0001.wav").is_file()

    resume_client = _FakeClient()
    encoder_resume = _FakeEncoder()
    mp3_paths = run(
        input_path=input_path,
        out_dir=out_dir,
        settings=settings,
        client=resume_client,
        encoder=encoder_resume,
    )

    assert [p.name for p in mp3_paths] == ["01_第1章.mp3", "02_第2章.mp3"]
    # Neither chapter 1 chunks nor chapter 2 chunk 1 should be requested again.
    assert resume_client.synthesized_texts == ["二章の二文目。"]
    assert len(encoder_resume.calls) == 1
    assert encoder_resume.calls[0].track == 2
    assert not (out_dir / settings.work_dir_name).exists()
    assert not (out_dir / settings.progress_file_name).exists()


@pytest.mark.requirement("REQ-2026-002-F09")
def test_pipeline_restarts_from_scratch_when_input_or_settings_change(
    tmp_path: Path,
) -> None:
    """T2S-I17: Progress and pipeline reset state and clear work_dir when input or settings change."""
    input_path = tmp_path / "book.md"
    input_path.write_text(
        "# 第1章\n一章の文。\n\n# 第2章\n二章の一文目。二章の二文目。\n",
        encoding="utf-8",
    )
    out_dir = tmp_path / "out"
    settings = Settings(speaker=1)

    # Crash on chapter 2 chunk 2 so chapter 1 is marked done and work/ch02/0001.wav remains.
    crashing_client = _FakeClient(crash_on_call=3)
    with pytest.raises(EngineError):
        run(
            input_path=input_path,
            out_dir=out_dir,
            settings=settings,
            client=crashing_client,
            encoder=_FakeEncoder(),
        )

    work_dir = out_dir / settings.work_dir_name
    progress_path = out_dir / settings.progress_file_name
    assert (work_dir / "ch02" / "0001.wav").is_file()

    # Verify Progress.load resets done_chapters and clears work_dir when fingerprint changes.
    changed_fp = fingerprint(input_path.read_bytes(), [], None, Settings(speaker=2))
    prog = Progress(progress_path=progress_path, work_dir=work_dir, fingerprint=changed_fp)
    state = prog.load()
    assert state.done_chapters == []
    assert list(work_dir.iterdir()) == []

    input_path.write_text(
        "# 第1章\n改訂された一章の文。\n\n# 第2章\n改訂された二章の文。\n",
        encoding="utf-8",
    )
    fresh_client = _FakeClient()
    fresh_encoder = _FakeEncoder()
    mp3_paths = run(
        input_path=input_path,
        out_dir=out_dir,
        settings=settings,
        client=fresh_client,
        encoder=fresh_encoder,
    )

    assert [p.name for p in mp3_paths] == ["01_第1章.mp3", "02_第2章.mp3"]
    assert fresh_client.synthesized_texts == ["改訂された一章の文。", "改訂された二章の文。"]
    assert len(fresh_encoder.calls) == 2


@pytest.mark.requirement("REQ-2026-002-F06")
@pytest.mark.requirement("REQ-2026-002-F08")
def test_pipeline_startup_check_failures_create_nothing_and_register_nothing(
    tmp_path: Path,
) -> None:
    """T2S-I21: pipeline.run creates nothing in out_dir and registers nothing when checks fail."""
    input_path = tmp_path / "input.txt"
    input_path.write_text("テスト本文です。", encoding="utf-8")
    dict_path = tmp_path / "dict.csv"
    dict_path.write_text(
        "surface,pronunciation,accent_type\nCO2,シーオーツー,5\n", encoding="utf-8"
    )

    # Missing input raises InputError before any engine or ffmpeg checks run.
    missing_input = tmp_path / "missing.txt"
    client_for_missing = _FakeClient(fail_check=True)
    with pytest.raises(InputError):
        run(
            input_path=missing_input,
            out_dir=tmp_path / "out_missing",
            settings=Settings(ffmpeg_path=str(tmp_path / "no_ffmpeg")),
            client=client_for_missing,
            encoder=_FakeEncoder(),
        )
    assert client_for_missing.check_calls == 0

    # Engine check failure leaves out_dir nonexistent and registers no dictionary entries.
    out_engine_fail = tmp_path / "out_engine_fail"
    failing_client = _FakeClient(fail_check=True)
    failing_encoder = _FakeEncoder()
    with pytest.raises(EngineError):
        run(
            input_path=input_path,
            out_dir=out_engine_fail,
            settings=Settings(dictionaries=(dict_path,)),
            client=failing_client,
            encoder=failing_encoder,
        )
    assert not out_engine_fail.exists()
    assert failing_client.registered == []
    assert failing_encoder.calls == []

    # FFmpeg check failure leaves out_dir nonexistent and registers no dictionary entries.
    out_ffmpeg_fail = tmp_path / "out_ffmpeg_fail"
    ok_client = _FakeClient()
    with pytest.raises(EngineError):
        run(
            input_path=input_path,
            out_dir=out_ffmpeg_fail,
            settings=Settings(
                ffmpeg_path=str(tmp_path / "nonexistent_ffmpeg_bin"),
                dictionaries=(dict_path,),
            ),
            client=ok_client,
            encoder=_FakeEncoder(),
        )
    assert not out_ffmpeg_fail.exists()
    assert ok_client.registered == []
