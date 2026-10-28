from pathlib import Path

import pytest

from src.txt2speech.audio import pause_frames
from src.txt2speech.config import Settings
from src.txt2speech.dictionary import DictEntry, parse_dictionary
from src.txt2speech.errors import InputError
from src.txt2speech.progress import Progress, fingerprint

_SAMPLE_RATE_24K = 24000


@pytest.mark.requirement("REQ-2026-002-F07")
def test_pause_frames_all_boundaries() -> None:
    """T2S-U16: pause_frames computes ms * 24000 // 1000 for all 4 boundary kinds."""
    settings = Settings()
    assert pause_frames("paragraph", settings, _SAMPLE_RATE_24K) == 900 * 24000 // 1000
    assert pause_frames("sentence", settings, _SAMPLE_RATE_24K) == 450 * 24000 // 1000
    assert pause_frames("comma", settings, _SAMPLE_RATE_24K) == 200 * 24000 // 1000
    assert pause_frames("other", settings, _SAMPLE_RATE_24K) == 100 * 24000 // 1000


@pytest.mark.requirement("REQ-2026-002-F03")
def test_parse_dictionary_valid_and_invalid_cases() -> None:
    """T2S-U17: parse_dictionary parses valid CSV, returns [] on empty, and reports source:line."""
    valid_csv = "surface,pronunciation,accent_type\nCO2,シーオーツー,5\npH,ペーハー,1\n"
    entries = parse_dictionary(valid_csv, "terms.csv")
    assert entries == [
        DictEntry(surface="CO2", pronunciation="シーオーツー", accent_type=5),
        DictEntry(surface="pH", pronunciation="ペーハー", accent_type=1),
    ]

    assert parse_dictionary("", "empty.csv") == []
    assert parse_dictionary("surface,pronunciation,accent_type\n", "header_only.csv") == []

    missing_col_csv = "surface,pronunciation,accent_type\nCO2,シーオーツー\n"
    with pytest.raises(InputError) as col_exc:
        parse_dictionary(missing_col_csv, "terms.csv")
    assert "terms.csv:2" in str(col_exc.value)

    bad_accent_csv = "surface,pronunciation,accent_type\nCO2,シーオーツー,not_an_int\n"
    with pytest.raises(InputError) as accent_exc:
        parse_dictionary(bad_accent_csv, "terms.csv")
    assert "terms.csv:2" in str(accent_exc.value)

    non_katakana_csv = "surface,pronunciation,accent_type\nCO2,しーおーつー,5\n"
    with pytest.raises(InputError) as kana_exc:
        parse_dictionary(non_katakana_csv, "terms.csv")
    assert "terms.csv:2" in str(kana_exc.value)


@pytest.mark.requirement("REQ-2026-002-F09")
def test_fingerprint_sensitivity_and_path_invariance() -> None:
    """T2S-U18: fingerprint matches on identical content/settings and cover path, differs otherwise."""
    base_settings = Settings(
        cover=Path("dir_a/cover.png"),
        album="物理基礎",
        voice_name="VOICEVOX",
    )
    base_fp = fingerprint(
        input_bytes="教科書本文A".encode(),
        dictionary_texts=["surface,pronunciation,accent_type\nCO2,シーオーツー,5\n"],
        cover_bytes=b"cover_bytes_v1",
        settings=base_settings,
    )

    # 1. Same input and settings -> identical.
    same_fp = fingerprint(
        input_bytes="教科書本文A".encode(),
        dictionary_texts=["surface,pronunciation,accent_type\nCO2,シーオーツー,5\n"],
        cover_bytes=b"cover_bytes_v1",
        settings=Settings(
            cover=Path("dir_a/cover.png"),
            album="物理基礎",
            voice_name="VOICEVOX",
        ),
    )
    assert same_fp == base_fp

    # 2. Input differs by 1 character -> different.
    diff_input_fp = fingerprint(
        input_bytes="教科書本文B".encode(),
        dictionary_texts=["surface,pronunciation,accent_type\nCO2,シーオーツー,5\n"],
        cover_bytes=b"cover_bytes_v1",
        settings=base_settings,
    )
    assert diff_input_fp != base_fp

    # 3. Speed scale differs -> different.
    diff_speed_fp = fingerprint(
        input_bytes="教科書本文A".encode(),
        dictionary_texts=["surface,pronunciation,accent_type\nCO2,シーオーツー,5\n"],
        cover_bytes=b"cover_bytes_v1",
        settings=Settings(
            cover=Path("dir_a/cover.png"),
            album="物理基礎",
            voice_name="VOICEVOX",
            speed_scale=1.2,
        ),
    )
    assert diff_speed_fp != base_fp

    # 4. Bitrate differs -> different.
    diff_bitrate_fp = fingerprint(
        input_bytes="教科書本文A".encode(),
        dictionary_texts=["surface,pronunciation,accent_type\nCO2,シーオーツー,5\n"],
        cover_bytes=b"cover_bytes_v1",
        settings=Settings(
            cover=Path("dir_a/cover.png"),
            album="物理基礎",
            voice_name="VOICEVOX",
            bitrate="192k",
        ),
    )
    assert diff_bitrate_fp != base_fp

    # 5. Cover image content differs -> different.
    diff_cover_bytes_fp = fingerprint(
        input_bytes="教科書本文A".encode(),
        dictionary_texts=["surface,pronunciation,accent_type\nCO2,シーオーツー,5\n"],
        cover_bytes=b"cover_bytes_v2",
        settings=base_settings,
    )
    assert diff_cover_bytes_fp != base_fp

    # 6. Only cover image path differs (content is the same) -> identical.
    diff_cover_path_fp = fingerprint(
        input_bytes="教科書本文A".encode(),
        dictionary_texts=["surface,pronunciation,accent_type\nCO2,シーオーツー,5\n"],
        cover_bytes=b"cover_bytes_v1",
        settings=Settings(
            cover=Path("dir_b/moved_cover.png"),
            album="物理基礎",
            voice_name="VOICEVOX",
        ),
    )
    assert diff_cover_path_fp == base_fp

    # 7. Album or voice_name differs -> different.
    diff_album_fp = fingerprint(
        input_bytes="教科書本文A".encode(),
        dictionary_texts=["surface,pronunciation,accent_type\nCO2,シーオーツー,5\n"],
        cover_bytes=b"cover_bytes_v1",
        settings=Settings(
            cover=Path("dir_a/cover.png"),
            album="化学基礎",
            voice_name="VOICEVOX",
        ),
    )
    diff_voice_fp = fingerprint(
        input_bytes="教科書本文A".encode(),
        dictionary_texts=["surface,pronunciation,accent_type\nCO2,シーオーツー,5\n"],
        cover_bytes=b"cover_bytes_v1",
        settings=Settings(
            cover=Path("dir_a/cover.png"),
            album="物理基礎",
            voice_name="OTHER_VOICE",
        ),
    )
    assert diff_album_fp != base_fp
    assert diff_voice_fp != base_fp

    # 8. Dictionary content differs -> different.
    diff_dict_fp = fingerprint(
        input_bytes="教科書本文A".encode(),
        dictionary_texts=["surface,pronunciation,accent_type\nCO2,シーオーツー,4\n"],
        cover_bytes=b"cover_bytes_v1",
        settings=base_settings,
    )
    assert diff_dict_fp != base_fp


@pytest.mark.requirement("REQ-2026-002-F09")
def test_progress_load_mark_mismatch_and_clear(tmp_path: Path) -> None:
    """T2S-U19: Progress persists done_chapters, resets on fingerprint mismatch, and clears files."""
    progress_path = tmp_path / ".txt2speech_progress.json"
    work_dir = tmp_path / ".txt2speech_work"
    chunk_file = work_dir / "ch01" / "0001.wav"
    chunk_file.parent.mkdir(parents=True, exist_ok=True)
    chunk_file.write_bytes(b"wav")

    writer = Progress(progress_path, work_dir, "fp_match")
    writer.mark_chapter_done(2)
    writer.mark_chapter_done(1)

    reader = Progress(progress_path, work_dir, "fp_match")
    loaded = reader.load()
    assert loaded.done_chapters == [1, 2]
    assert loaded.done_chapters == [1, 2]
    assert chunk_file.is_file()

    mismatch = Progress(progress_path, work_dir, "fp_other")
    reset_state = mismatch.load()
    assert reset_state.done_chapters == []
    assert list(work_dir.iterdir()) == []

    mismatch.mark_chapter_done(1)
    (work_dir / "temp.wav").write_bytes(b"wav")
    mismatch.clear()
    assert not progress_path.exists()
    assert not work_dir.exists()
