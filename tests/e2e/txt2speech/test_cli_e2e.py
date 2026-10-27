import json
import os
import re
import socket
import struct
import subprocess
import sys
import zlib
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import pytest

from src.txt2speech.chunking import halve
from src.txt2speech.config import (
    DEFAULT_MIN_CHUNK_CHARS,
    DEFAULT_PROGRESS_FILE_NAME,
    DEFAULT_WORK_DIR_NAME,
)
from src.txt2speech.preprocess import normalize
from src.txt2speech.structure import split_chapters
from tests.e2e.txt2speech.conftest import FakeVoicevoxServer

_PROJECT_ROOT_DEPTH = 3
_PROJECT_ROOT = Path(__file__).resolve().parents[_PROJECT_ROOT_DEPTH]

_FFMPEG_BIN = "/usr/bin/ffmpeg"
_FFPROBE_BIN = "/usr/bin/ffprobe"

_EXIT_OK = 0
_EXIT_INPUT_ERROR = 2
_EXIT_ENGINE_ERROR = 3

_EXPECTED_SAMPLE_RATE_STR = "44100"
_EXPECTED_CHANNELS = 1
_MIN_128K_BITRATE = 115_000
_MAX_128K_BITRATE = 140_000
_MIN_96K_BITRATE = 85_000
_MAX_96K_BITRATE = 110_000

_TARGET_LUFS = -16.0
_LUFS_TOLERANCE = 1.0
_MAX_TRUE_PEAK_DBFS = -0.9

_EXPECTED_MAX_IN_FLIGHT = 1
_EXPECTED_RETRY_SYNTH_CALLS = 2
_EXPECTED_DICT_ENTRIES = 2
_EXHAUST_THRESHOLD_CHARS = 15
_CHAPTER_ONE_CHUNK_COUNT = 2
_SINGLE_CHUNK_COUNT = 1

_LOOPBACK_HOST = "127.0.0.1"
_EPHEMERAL_PORT = 0
_CONFIGURED_SPEED_SCALE = 1.15
_CLI_OVERRIDE_SPEAKER = "3"
_EXTERNAL_ENGINE_URL = "http://example.com:50021"

_TEN_K_CHAPTERS = 4
_TEN_K_SENTENCES_PER_CHAPTER = 50
_MIN_TOTAL_TEN_K_CHARS = 10_000

_PNG_WIDTH = 1
_PNG_HEIGHT = 1
_PNG_BIT_DEPTH = 8
_PNG_COLOR_TYPE_RGB = 2
_CRC32_MASK = 0xFFFFFFFF

_EBUR128_INTEGRATED_RE = re.compile(r"\bI:\s*(-?\d+(?:\.\d+)?)\s*LUFS")
_EBUR128_TRUE_PEAK_RE = re.compile(r"\bPeak:\s*(-?\d+(?:\.\d+)?)\s*dBFS")
_WHITESPACE_RE = re.compile(r"\s+")


def _run_cli(
    args: Sequence[str],
    extra_env: Mapping[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    if extra_env is not None:
        env.update(extra_env)
    cmd = [sys.executable, "-m", "src.txt2speech", *args]
    # Execute the CLI module in a real child Python process from the project root.
    return subprocess.run(  # noqa: S603
        cmd,
        cwd=_PROJECT_ROOT,
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )


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
    # Run ffprobe against a test-generated MP3 file inside tmp_path.
    proc = subprocess.run(cmd, capture_output=True, text=True, check=True)  # noqa: S603
    loaded: dict[str, Any] = json.loads(proc.stdout)
    return loaded


def _measure_ebur128(path: Path) -> tuple[float, float]:
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
    # Run ffmpeg ebur128 filter against a test-generated MP3 file inside tmp_path.
    proc = subprocess.run(cmd, capture_output=True, text=True, check=True)  # noqa: S603
    i_matches = _EBUR128_INTEGRATED_RE.findall(proc.stderr)
    tp_matches = _EBUR128_TRUE_PEAK_RE.findall(proc.stderr)
    assert i_matches, f"Integrated loudness not found in stderr: {proc.stderr}"
    assert tp_matches, f"True peak not found in stderr: {proc.stderr}"
    return float(i_matches[-1]), float(tp_matches[-1])


def _png_chunk(chunk_type: bytes, data: bytes) -> bytes:
    crc = zlib.crc32(chunk_type + data) & _CRC32_MASK
    return struct.pack(">I", len(data)) + chunk_type + data + struct.pack(">I", crc)


def _write_minimal_png(path: Path) -> None:
    signature = b"\x89PNG\r\n\x1a\n"
    ihdr_data = struct.pack(
        ">IIBBBBB",
        _PNG_WIDTH,
        _PNG_HEIGHT,
        _PNG_BIT_DEPTH,
        _PNG_COLOR_TYPE_RGB,
        0,
        0,
        0,
    )
    ihdr = _png_chunk(b"IHDR", ihdr_data)
    idat = _png_chunk(b"IDAT", zlib.compress(b"\x00\xff\x00\x00"))
    iend = _png_chunk(b"IEND", b"")
    path.write_bytes(signature + ihdr + idat + iend)


def _find_unused_local_url() -> str:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind((_LOOPBACK_HOST, _EPHEMERAL_PORT))
        port = sock.getsockname()[1]
    return f"http://{_LOOPBACK_HOST}:{port}"


def _build_ten_thousand_char_text() -> str:
    chapters: list[str] = []
    for ch_no in range(1, _TEN_K_CHAPTERS + 1):
        sentences = [
            f"これは第{ch_no}章の学習内容を確認するための短いテスト文であり、"
            f"順番に音声合成エンジンへ送信される文番号{sent_no}です。"
            for sent_no in range(1, _TEN_K_SENTENCES_PER_CHAPTER + 1)
        ]
        chapter_block = f"# 第{ch_no}章 学習単元{ch_no}\n" + "\n".join(sentences)
        chapters.append(chapter_block)
    return "\n\n".join(chapters) + "\n"


@pytest.mark.requirement("REQ-2026-002-F04")
@pytest.mark.requirement("REQ-2026-002-F10")
def test_e01_utf8_chapter_headings_create_mp3s_and_print_paths(
    tmp_path: Path,
    fake_voicevox: FakeVoicevoxServer,
) -> None:
    """T2S-E01: UTF-8 text with 第1章 and 第2章 produces 01_第1章.mp3 and 02_第2章.mp3."""
    input_path = tmp_path / "textbook.txt"
    input_path.write_text(
        "第1章\n最初の章の本文です。\n\n第2章\n次の章の本文です。\n",
        encoding="utf-8",
    )
    out_dir = tmp_path / "out"

    result = _run_cli([str(input_path), "-o", str(out_dir), "--engine-url", fake_voicevox.url])

    assert result.returncode == _EXIT_OK
    expected_files = [out_dir / "01_第1章.mp3", out_dir / "02_第2章.mp3"]
    assert all(p.is_file() for p in expected_files)
    assert result.stdout.splitlines() == [str(p) for p in expected_files]


@pytest.mark.requirement("REQ-2026-002-F04")
def test_e02_headingless_text_creates_single_mp3_with_stem_title(
    tmp_path: Path,
    fake_voicevox: FakeVoicevoxServer,
) -> None:
    """T2S-E02: Headingless short text produces 1 MP3 whose ID3 title is the input stem."""
    input_path = tmp_path / "short_note.txt"
    input_path.write_text("見出しのない短いテキストです。二文目です。\n", encoding="utf-8")
    out_dir = tmp_path / "out"

    result = _run_cli([str(input_path), "-o", str(out_dir), "--engine-url", fake_voicevox.url])

    assert result.returncode == _EXIT_OK
    mp3_path = out_dir / "01.mp3"
    assert mp3_path.is_file()
    assert result.stdout.splitlines() == [str(mp3_path)]

    probe = _probe_mp3(mp3_path)
    tags = {k.lower(): v for k, v in probe["format"]["tags"].items()}
    assert tags["title"] == "short_note"


@pytest.mark.requirement("REQ-2026-002-F01")
def test_e03_shift_jis_input_decoded_without_mojibake(
    tmp_path: Path,
    fake_voicevox: FakeVoicevoxServer,
) -> None:
    """T2S-E03: Shift_JIS (CP932) input succeeds and sends uncorrupted Japanese text."""
    input_path = tmp_path / "sjis_book.txt"
    expected_sentence = "シフトジスで保存された日本語の文章が文字化けせずに読めます。"
    raw_cp932 = f"第1章\n{expected_sentence}\n".encode("cp932")
    input_path.write_bytes(raw_cp932)
    out_dir = tmp_path / "out"

    result = _run_cli([str(input_path), "-o", str(out_dir), "--engine-url", fake_voicevox.url])

    assert result.returncode == _EXIT_OK
    assert fake_voicevox.synthesized_texts == [expected_sentence]


@pytest.mark.requirement("REQ-2026-002-F02")
def test_e04_three_ruby_notations_send_readings_only(
    tmp_path: Path,
    fake_voicevox: FakeVoicevoxServer,
) -> None:
    """T2S-E04: Text with Aozora, Markdown, and HTML ruby notations sends readings only."""
    input_path = tmp_path / "ruby.md"
    input_path.write_text(
        "第1章\n"
        "漢字《かんじ》と[単語](たんご)と"
        "<ruby>表現<rp>(</rp><rt>ひょうげん</rt><rp>)</rp></ruby>を学ぶ。\n",
        encoding="utf-8",
    )
    out_dir = tmp_path / "out"

    result = _run_cli([str(input_path), "-o", str(out_dir), "--engine-url", fake_voicevox.url])

    assert result.returncode == _EXIT_OK
    assert fake_voicevox.synthesized_texts == ["かんじとたんごとひょうげんを学ぶ。"]
    combined = "".join(fake_voicevox.synthesized_texts)
    assert "漢字" not in combined
    assert "単語" not in combined
    assert "表現" not in combined


@pytest.mark.requirement("REQ-2026-002-F06")
def test_e05_unreachable_engine_exits_with_code_3_and_leaves_no_files(
    tmp_path: Path,
) -> None:
    """T2S-E05: Unused local port exits with code 3, names URL in stderr, and writes nothing."""
    input_path = tmp_path / "input.txt"
    input_path.write_text("第1章\nテスト本文です。\n", encoding="utf-8")
    out_dir = tmp_path / "out"
    unused_url = _find_unused_local_url()

    result = _run_cli([str(input_path), "-o", str(out_dir), "--engine-url", unused_url])

    assert result.returncode == _EXIT_ENGINE_ERROR
    assert unused_url in result.stderr
    assert result.stdout == ""
    assert list(out_dir.glob("*.mp3")) == []
    assert list(out_dir.glob(".txt2speech_*")) == []


@pytest.mark.requirement("REQ-2026-002-F10")
def test_e06_nonexistent_input_exits_with_code_2_and_names_file(
    tmp_path: Path,
    fake_voicevox: FakeVoicevoxServer,
) -> None:
    """T2S-E06: Nonexistent input file exits with code 2 and names the missing file in stderr."""
    missing_input = tmp_path / "no_such_textbook.txt"
    out_dir = tmp_path / "out"

    result = _run_cli([str(missing_input), "-o", str(out_dir), "--engine-url", fake_voicevox.url])

    assert result.returncode == _EXIT_INPUT_ERROR
    assert missing_input.name in result.stderr
    assert result.stdout == ""


@pytest.mark.requirement("REQ-2026-002-F08")
def test_e07_generated_mp3_format_stream_and_id3_tags(
    tmp_path: Path,
    fake_voicevox: FakeVoicevoxServer,
) -> None:
    """T2S-E07: ffprobe confirms mp3 format, 44100 Hz, mono, ~128 kbps, and ID3v2.4 metadata."""
    input_path = tmp_path / "biology_text.md"
    input_path.write_text(
        "# 第1章 細胞の構造\n"
        "生物の最小単位である細胞の構造と働きについて詳しく説明します。\n\n"
        "# 第2章 遺伝のしくみ\n"
        "親から子へと形質が受け継がれる遺伝の法則について詳しく説明します。\n",
        encoding="utf-8",
    )
    out_dir = tmp_path / "out"

    result = _run_cli([str(input_path), "-o", str(out_dir), "--engine-url", fake_voicevox.url])

    assert result.returncode == _EXIT_OK
    mp3_one = out_dir / "01_第1章 細胞の構造.mp3"
    mp3_two = out_dir / "02_第2章 遺伝のしくみ.mp3"
    assert mp3_one.is_file()
    assert mp3_two.is_file()

    probe_one = _probe_mp3(mp3_one)
    assert "mp3" in probe_one["format"]["format_name"]
    stream_one = probe_one["streams"][0]
    assert stream_one["codec_name"] == "mp3"
    assert stream_one["sample_rate"] == _EXPECTED_SAMPLE_RATE_STR
    assert stream_one["channels"] == _EXPECTED_CHANNELS
    bitrate_one = int(stream_one.get("bit_rate", probe_one["format"]["bit_rate"]))
    assert _MIN_128K_BITRATE <= bitrate_one <= _MAX_128K_BITRATE

    tags_one = {k.lower(): v for k, v in probe_one["format"]["tags"].items()}
    assert tags_one["title"] == "第1章 細胞の構造"
    assert tags_one["artist"] == "VOICEVOX"
    assert tags_one["album"] == "biology_text"
    assert tags_one["track"] == "1"
    assert tags_one["genre"] == "Audiobook"

    probe_two = _probe_mp3(mp3_two)
    tags_two = {k.lower(): v for k, v in probe_two["format"]["tags"].items()}
    assert tags_two["title"] == "第2章 遺伝のしくみ"
    assert tags_two["track"] == "2"


@pytest.mark.requirement("REQ-2026-002-F08")
def test_e08_missing_ffmpeg_exits_with_code_3_before_audio_query(
    tmp_path: Path,
    fake_voicevox: FakeVoicevoxServer,
) -> None:
    """T2S-E08: --ffmpeg /nonexistent/ffmpeg exits with code 3 and sends no /audio_query."""
    input_path = tmp_path / "input.txt"
    input_path.write_text("第1章\nテストの本文です。\n", encoding="utf-8")
    out_dir = tmp_path / "out"

    result = _run_cli(
        [
            str(input_path),
            "-o",
            str(out_dir),
            "--ffmpeg",
            "/nonexistent/ffmpeg",
            "--engine-url",
            fake_voicevox.url,
        ]
    )

    assert result.returncode == _EXIT_ENGINE_ERROR
    assert "/nonexistent/ffmpeg" in result.stderr
    assert fake_voicevox.synthesized_texts == []
    assert [r for r in fake_voicevox.requests if r.path == "/audio_query"] == []


@pytest.mark.requirement("REQ-2026-002-F05")
@pytest.mark.requirement("REQ-2026-002-F06")
def test_e09_ten_thousand_chars_multi_chapter_sequential_accuracy(
    tmp_path: Path,
    fake_voicevox: FakeVoicevoxServer,
) -> None:
    """T2S-E09: ~10,000 chars over multiple chapters preserves preprocessed text and max_in_flight=1."""
    raw_text = _build_ten_thousand_char_text()
    assert len(raw_text) >= _MIN_TOTAL_TEN_K_CHARS
    input_path = tmp_path / "large_textbook.md"
    input_path.write_text(raw_text, encoding="utf-8")
    out_dir = tmp_path / "out"
    config_path = tmp_path / "fast_pause.yaml"
    config_path.write_text(
        "pause_ms:\n  paragraph: 10\n  sentence: 10\n  comma: 10\n  other: 10\n",
        encoding="utf-8",
    )

    result = _run_cli(
        [
            str(input_path),
            "-o",
            str(out_dir),
            "--config",
            str(config_path),
            "--engine-url",
            fake_voicevox.url,
        ]
    )

    assert result.returncode == _EXIT_OK
    created_mp3s = sorted(out_dir.glob("*.mp3"))
    assert len(created_mp3s) == _TEN_K_CHAPTERS
    assert fake_voicevox.max_in_flight == _EXPECTED_MAX_IN_FLIGHT

    expected_preprocessed = "".join(normalize(chapter.body) for chapter in split_chapters(raw_text))
    expected_compact = _WHITESPACE_RE.sub("", expected_preprocessed)
    received_compact = _WHITESPACE_RE.sub("", "".join(fake_voicevox.synthesized_texts))
    assert received_compact == expected_compact


@pytest.mark.requirement("REQ-2026-002-F06")
def test_e10_transient_503_on_synthesis_succeeds_after_retry(
    tmp_path: Path,
    fake_voicevox: FakeVoicevoxServer,
) -> None:
    """T2S-E10: First /synthesis returning 503 is retried and succeeds."""
    fake_voicevox.fail_synthesis_first = 1
    input_path = tmp_path / "retry.txt"
    input_path.write_text("第1章\n一時的なエラーから回復する文です。\n", encoding="utf-8")
    config_path = tmp_path / "config.yaml"
    config_path.write_text("retry_wait_seconds: 0.01\n", encoding="utf-8")
    out_dir = tmp_path / "out"

    result = _run_cli(
        [
            str(input_path),
            "-o",
            str(out_dir),
            "--config",
            str(config_path),
            "--engine-url",
            fake_voicevox.url,
        ]
    )

    assert result.returncode == _EXIT_OK
    assert (out_dir / "01_第1章.mp3").is_file()
    synth_requests = [r for r in fake_voicevox.requests if r.path == "/synthesis"]
    assert len(synth_requests) == _EXPECTED_RETRY_SYNTH_CALLS


@pytest.mark.requirement("REQ-2026-002-F08")
def test_e11_output_dir_with_nonexistent_parent_is_created(
    tmp_path: Path,
    fake_voicevox: FakeVoicevoxServer,
) -> None:
    """T2S-E11: Output directory with nonexistent parent directories is created automatically."""
    input_path = tmp_path / "input.txt"
    input_path.write_text(
        "第1章\n親ディレクトリが存在しない出力先のテストです。\n", encoding="utf-8"
    )
    out_dir = tmp_path / "missing_parent" / "deep_child" / "out"
    assert not out_dir.parent.exists()

    result = _run_cli([str(input_path), "-o", str(out_dir), "--engine-url", fake_voicevox.url])

    assert result.returncode == _EXIT_OK
    assert (out_dir / "01_第1章.mp3").is_file()


@pytest.mark.requirement("REQ-2026-002-F04")
def test_e12_numbered_section_headings_split_into_two_chapters(
    tmp_path: Path,
    fake_voicevox: FakeVoicevoxServer,
) -> None:
    """T2S-E12: Numbered section headings 1.1 概要 and 1.2 方法 split into 2 MP3 files."""
    input_path = tmp_path / "sections.txt"
    input_path.write_text(
        "1.1 概要\n概要に関する説明文です。\n\n1.2 方法\n方法に関する説明文です。\n",
        encoding="utf-8",
    )
    out_dir = tmp_path / "out"

    result = _run_cli([str(input_path), "-o", str(out_dir), "--engine-url", fake_voicevox.url])

    assert result.returncode == _EXIT_OK
    expected_files = [out_dir / "01_1.1 概要.mp3", out_dir / "02_1.2 方法.mp3"]
    assert all(p.is_file() for p in expected_files)
    assert result.stdout.splitlines() == [str(p) for p in expected_files]


@pytest.mark.requirement("REQ-2026-002-F04")
def test_e22_sentence_starting_with_chapter_number_is_not_a_heading(
    tmp_path: Path,
    fake_voicevox: FakeVoicevoxServer,
) -> None:
    """T2S-E22: a body sentence starting with 第1章でも… stays one untitled chapter."""
    input_path = tmp_path / "book.txt"
    input_path.write_text(
        "第1章でも簡単に触れたが、追い風が吹いているのは間違いない。\n", encoding="utf-8"
    )
    out_dir = tmp_path / "out"

    result = _run_cli([str(input_path), "-o", str(out_dir), "--engine-url", fake_voicevox.url])

    assert result.returncode == _EXIT_OK
    assert [p.name for p in out_dir.glob("*.mp3")] == ["01.mp3"]


@pytest.mark.requirement("REQ-2026-002-F08")
def test_e13_mp3_integrated_loudness_and_true_peak(
    tmp_path: Path,
    fake_voicevox: FakeVoicevoxServer,
) -> None:
    """T2S-E13: Generated MP3 integrated loudness is -16±1.0 LUFS and true peak <= -0.9 dBFS."""
    input_path = tmp_path / "loudness.txt"
    # Provide ~150 characters (~12 seconds of audio) so EBU R128 gating has ample signal.
    input_path.write_text(
        "第1章\n"
        "ラウドネス正規化の精度を確かめるために十分な長さを持つ日本語の文章を入力します。"
        "二文目も続けて読み上げることで安定した統合ラウドネスとトゥルーピークを測定します。"
        "三文目も追加して全体の再生時間を十分に確保します。\n",
        encoding="utf-8",
    )
    out_dir = tmp_path / "out"

    result = _run_cli([str(input_path), "-o", str(out_dir), "--engine-url", fake_voicevox.url])

    assert result.returncode == _EXIT_OK
    mp3_path = out_dir / "01_第1章.mp3"
    assert mp3_path.is_file()

    integrated_lufs, true_peak_dbfs = _measure_ebur128(mp3_path)
    assert abs(integrated_lufs - _TARGET_LUFS) <= _LUFS_TOLERANCE
    assert true_peak_dbfs <= _MAX_TRUE_PEAK_DBFS


@pytest.mark.requirement("REQ-2026-002-F08")
def test_e14_cover_option_embeds_attached_picture_stream(
    tmp_path: Path,
    fake_voicevox: FakeVoicevoxServer,
) -> None:
    """T2S-E14: --cover embeds an attached-picture video stream; without --cover there is none."""
    input_path = tmp_path / "book.txt"
    input_path.write_text("第1章\nカバーアートの確認用の文章です。\n", encoding="utf-8")
    cover_path = tmp_path / "cover.png"
    _write_minimal_png(cover_path)

    out_with_cover = tmp_path / "out_with_cover"
    res_with = _run_cli(
        [
            str(input_path),
            "-o",
            str(out_with_cover),
            "--cover",
            str(cover_path),
            "--engine-url",
            fake_voicevox.url,
        ]
    )
    assert res_with.returncode == _EXIT_OK
    streams_with = _probe_mp3(out_with_cover / "01_第1章.mp3")["streams"]
    video_streams = [s for s in streams_with if s["codec_type"] == "video"]
    assert len(video_streams) == 1
    assert video_streams[0]["disposition"]["attached_pic"] == 1

    out_without_cover = tmp_path / "out_without_cover"
    res_without = _run_cli(
        [
            str(input_path),
            "-o",
            str(out_without_cover),
            "--engine-url",
            fake_voicevox.url,
        ]
    )
    assert res_without.returncode == _EXIT_OK
    streams_without = _probe_mp3(out_without_cover / "01_第1章.mp3")["streams"]
    assert [s["codec_type"] for s in streams_without] == ["audio"]


@pytest.mark.requirement("REQ-2026-002-F03")
def test_e15_dictionary_csv_registered_before_audio_query_and_bad_csv_fails(
    tmp_path: Path,
    fake_voicevox: FakeVoicevoxServer,
) -> None:
    """T2S-E15: --dictionary sends /user_dict_word before /audio_query; malformed CSV exits 2."""
    input_path = tmp_path / "input.txt"
    input_path.write_text("第1章\n専門用語を含む本文です。\n", encoding="utf-8")
    valid_csv = tmp_path / "terms.csv"
    valid_csv.write_text(
        "surface,pronunciation,accent_type\nCO2,シーオーツー,5\npH,ペーハー,1\n",
        encoding="utf-8",
    )
    out_dir = tmp_path / "out"

    result = _run_cli(
        [
            str(input_path),
            "-o",
            str(out_dir),
            "--dictionary",
            str(valid_csv),
            "--engine-url",
            fake_voicevox.url,
        ]
    )

    assert result.returncode == _EXIT_OK
    dict_indices = [
        idx for idx, req in enumerate(fake_voicevox.requests) if req.path == "/user_dict_word"
    ]
    query_indices = [
        idx for idx, req in enumerate(fake_voicevox.requests) if req.path == "/audio_query"
    ]
    assert len(dict_indices) == _EXPECTED_DICT_ENTRIES
    assert query_indices
    assert max(dict_indices) < min(query_indices)
    assert fake_voicevox.requests[dict_indices[0]].query == {
        "surface": "CO2",
        "pronunciation": "シーオーツー",
        "accent_type": "5",
    }
    assert fake_voicevox.requests[dict_indices[1]].query == {
        "surface": "pH",
        "pronunciation": "ペーハー",
        "accent_type": "1",
    }

    bad_csv = tmp_path / "malformed.csv"
    bad_csv.write_text(
        "surface,pronunciation,accent_type\nCO2,シーオーツー,5\nbad_term,ひらがな,not_int\n",
        encoding="utf-8",
    )
    bad_result = _run_cli(
        [
            str(input_path),
            "-o",
            str(tmp_path / "out_bad"),
            "--dictionary",
            str(bad_csv),
            "--engine-url",
            fake_voicevox.url,
        ]
    )
    assert bad_result.returncode == _EXIT_INPUT_ERROR
    assert f"{bad_csv}:3" in bad_result.stderr


@pytest.mark.requirement("REQ-2026-002-F06")
def test_e16_chunk_halving_on_500_and_always_500_exits_with_code_3(
    tmp_path: Path,
    fake_voicevox: FakeVoicevoxServer,
) -> None:
    """T2S-E16: Long chunks failing with 500 succeed after halving; always_500 exits with code 3."""
    sentence = "これはメモリ不足を模擬するためのテスト文です。"
    halved = halve(sentence, DEFAULT_MIN_CHUNK_CHARS)
    assert halved is not None
    first_half, second_half = halved

    input_path = tmp_path / "halving.txt"
    input_path.write_text(f"第1章\n{sentence}\n", encoding="utf-8")
    out_dir = tmp_path / "out_ok"
    fake_voicevox.exhaust_above_chars = _EXHAUST_THRESHOLD_CHARS

    result = _run_cli([str(input_path), "-o", str(out_dir), "--engine-url", fake_voicevox.url])

    assert result.returncode == _EXIT_OK
    assert (out_dir / "01_第1章.mp3").is_file()
    assert first_half in fake_voicevox.synthesized_texts
    assert second_half in fake_voicevox.synthesized_texts

    fake_voicevox.always_500 = True
    fail_result = _run_cli(
        [
            str(input_path),
            "-o",
            str(tmp_path / "out_fail"),
            "--engine-url",
            fake_voicevox.url,
        ]
    )
    assert fail_result.returncode == _EXIT_ENGINE_ERROR


@pytest.mark.requirement("REQ-2026-002-F09")
def test_e17_resume_skips_completed_chapter_and_cleans_up(
    tmp_path: Path,
    fake_voicevox: FakeVoicevoxServer,
) -> None:
    """T2S-E17: Rerunning after chapter 2 failure skips chapter 1 chunks and cleans up temp files."""
    input_path = tmp_path / "resume.md"
    input_path.write_text(
        "# 第1章\n一章の最初の文です。一章の二番目の文です。\n\n"
        "# 第2章\n二章の最初の文です。二章の二番目の文です。\n",
        encoding="utf-8",
    )
    out_dir = tmp_path / "out"
    fake_voicevox.fail_after_n_synthesis = _CHAPTER_ONE_CHUNK_COUNT

    first_run = _run_cli([str(input_path), "-o", str(out_dir), "--engine-url", fake_voicevox.url])

    assert first_run.returncode == _EXIT_ENGINE_ERROR
    assert (out_dir / "01_第1章.mp3").is_file()
    assert not (out_dir / "02_第2章.mp3").exists()
    assert (out_dir / DEFAULT_PROGRESS_FILE_NAME).is_file()

    fake_voicevox.fail_after_n_synthesis = None
    fake_voicevox.synthesized_texts.clear()
    fake_voicevox.requests.clear()

    second_run = _run_cli([str(input_path), "-o", str(out_dir), "--engine-url", fake_voicevox.url])

    assert second_run.returncode == _EXIT_OK
    assert fake_voicevox.synthesized_texts == [
        "二章の最初の文です。",
        "二章の二番目の文です。",
    ]
    assert (out_dir / "01_第1章.mp3").is_file()
    assert (out_dir / "02_第2章.mp3").is_file()
    assert not (out_dir / DEFAULT_WORK_DIR_NAME).exists()
    assert not (out_dir / DEFAULT_PROGRESS_FILE_NAME).exists()


@pytest.mark.requirement("REQ-2026-002-F09")
def test_e18_resume_discards_progress_when_input_changes(
    tmp_path: Path,
    fake_voicevox: FakeVoicevoxServer,
) -> None:
    """T2S-E18: Modifying the input file before rerun discards progress and resynthesizes all."""
    input_path = tmp_path / "changing.md"
    input_path.write_text(
        "# 第1章\n変更前の一章の文です。\n\n# 第2章\n変更前の二章の文です。\n",
        encoding="utf-8",
    )
    out_dir = tmp_path / "out"
    fake_voicevox.fail_after_n_synthesis = _SINGLE_CHUNK_COUNT

    first_run = _run_cli([str(input_path), "-o", str(out_dir), "--engine-url", fake_voicevox.url])
    assert first_run.returncode == _EXIT_ENGINE_ERROR
    assert (out_dir / "01_第1章.mp3").is_file()
    assert (out_dir / DEFAULT_PROGRESS_FILE_NAME).is_file()

    input_path.write_text(
        "# 第1章\n書き換え後の一章の文です。\n\n# 第2章\n書き換え後の二章の文です。\n",
        encoding="utf-8",
    )
    fake_voicevox.fail_after_n_synthesis = None
    fake_voicevox.synthesized_texts.clear()
    fake_voicevox.requests.clear()

    second_run = _run_cli([str(input_path), "-o", str(out_dir), "--engine-url", fake_voicevox.url])

    assert second_run.returncode == _EXIT_OK
    assert fake_voicevox.synthesized_texts == [
        "書き換え後の一章の文です。",
        "書き換え後の二章の文です。",
    ]
    assert (out_dir / "01_第1章.mp3").is_file()
    assert (out_dir / "02_第2章.mp3").is_file()
    assert not (out_dir / DEFAULT_WORK_DIR_NAME).exists()
    assert not (out_dir / DEFAULT_PROGRESS_FILE_NAME).exists()


@pytest.mark.requirement("REQ-2026-002-F10")
def test_e19_config_yaml_and_cli_override_precedence(
    tmp_path: Path,
    fake_voicevox: FakeVoicevoxServer,
) -> None:
    """T2S-E19: --config YAML sets speed_scale/pause/bitrate and CLI --speaker overrides YAML."""
    input_path = tmp_path / "config_test.txt"
    input_path.write_text("第1章\n設定ファイルの優先順位を確認する文です。\n", encoding="utf-8")
    config_path = tmp_path / "settings.yaml"
    config_path.write_text(
        "speaker: 1\n"
        "speed_scale: 1.15\n"
        "bitrate: 96k\n"
        "pause_ms:\n"
        "  paragraph: 500\n"
        "  sentence: 300\n"
        "  comma: 150\n"
        "  other: 80\n",
        encoding="utf-8",
    )
    out_dir = tmp_path / "out"

    result = _run_cli(
        [
            str(input_path),
            "-o",
            str(out_dir),
            "--config",
            str(config_path),
            "--speaker",
            _CLI_OVERRIDE_SPEAKER,
            "--engine-url",
            fake_voicevox.url,
        ]
    )

    assert result.returncode == _EXIT_OK
    query_reqs = [r for r in fake_voicevox.requests if r.path == "/audio_query"]
    synth_reqs = [r for r in fake_voicevox.requests if r.path == "/synthesis"]
    assert len(query_reqs) == 1
    assert len(synth_reqs) == 1
    assert query_reqs[0].query["speaker"] == _CLI_OVERRIDE_SPEAKER
    assert synth_reqs[0].query["speaker"] == _CLI_OVERRIDE_SPEAKER
    assert synth_reqs[0].json_body["speedScale"] == _CONFIGURED_SPEED_SCALE

    probe = _probe_mp3(out_dir / "01_第1章.mp3")
    stream_bitrate = int(probe["streams"][0].get("bit_rate", probe["format"]["bit_rate"]))
    assert _MIN_96K_BITRATE <= stream_bitrate <= _MAX_96K_BITRATE


@pytest.mark.requirement("REQ-2026-002-F11")
def test_e20_external_engine_url_rejected_with_exit_code_2(
    tmp_path: Path,
    fake_voicevox: FakeVoicevoxServer,
) -> None:
    """T2S-E20: --engine-url http://example.com:50021 exits with code 2 without contacting server."""
    input_path = tmp_path / "input.txt"
    input_path.write_text("第1章\n外部送信禁止の確認です。\n", encoding="utf-8")
    out_dir = tmp_path / "out"

    result = _run_cli([str(input_path), "-o", str(out_dir), "--engine-url", _EXTERNAL_ENGINE_URL])

    assert result.returncode == _EXIT_INPUT_ERROR
    assert _EXTERNAL_ENGINE_URL in result.stderr
    assert fake_voicevox.requests == []


@pytest.mark.requirement("REQ-2026-002-F10")
def test_e21_progress_output_on_stderr_and_paths_only_on_stdout(
    tmp_path: Path,
    fake_voicevox: FakeVoicevoxServer,
) -> None:
    """T2S-E21: CLI writes tqdm chapter/chunk progress to stderr and only MP3 paths to stdout."""
    input_path = tmp_path / "progress.md"
    input_path.write_text(
        "# 第1章\n一章の一文目です。一章の二文目です。\n\n# 第2章\n二章の文です。\n",
        encoding="utf-8",
    )
    out_dir = tmp_path / "out"

    result = _run_cli([str(input_path), "-o", str(out_dir), "--engine-url", fake_voicevox.url])

    assert result.returncode == _EXIT_OK
    expected_paths = [
        str(out_dir / "01_第1章.mp3"),
        str(out_dir / "02_第2章.mp3"),
    ]
    assert result.stdout.splitlines() == expected_paths
    assert "章 1/2" in result.stderr
    assert "章 2/2" in result.stderr
    assert "chunk" in result.stderr
