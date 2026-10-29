from pathlib import Path

import pytest

from src.summarize.store import load, save, write_atomic

_SAMPLE_KEY = "testkey12345678"
_OTHER_KEY = "otherkey87654321"
_ORIGINAL_SUMMARY = "# 旧サマリー\n\n既存の古い要約文です。\n"
_NEW_SUMMARY = "# 新サマリー\n\n新しく生成された要約文です。\n"


@pytest.mark.requirement("REQ-2026-003-F06")
def test_sum_i08_store_roundtrip_and_missing_keys(tmp_path: Path) -> None:
    """SUM-I08: store saves and loads Japanese text, returning None for differing keys or indices."""
    work_dir = tmp_path / ".summarize_work"
    text = "第1章の日本語要約本文。\n改行や記号「」、!?を含みます。"

    save(work_dir, 1, _SAMPLE_KEY, text)
    loaded = load(work_dir, 1, _SAMPLE_KEY)
    assert loaded == text

    # Missing entry for different key
    assert load(work_dir, 1, _OTHER_KEY) is None
    # Missing entry for different index
    assert load(work_dir, 2, _SAMPLE_KEY) is None

    # Saving under a different key leaves the existing key intact
    save(work_dir, 1, _OTHER_KEY, "別の要約本文")
    assert load(work_dir, 1, _SAMPLE_KEY) == text
    assert load(work_dir, 1, _OTHER_KEY) == "別の要約本文"
    assert len(list(work_dir.glob("01_*.txt"))) == 2


@pytest.mark.requirement("REQ-2026-003-F05")
def test_sum_i09_write_atomic_preserves_existing_file_and_cleans_tmp_on_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """SUM-I09: write_atomic leaves existing file untouched and cleans up .tmp when replace fails."""
    summary_path = tmp_path / "summary.md"
    summary_path.write_text(_ORIGINAL_SUMMARY, encoding="utf-8")

    def fail_replace(self: Path, target: Path) -> Path:
        msg = "Simulated atomic replacement failure"
        raise OSError(msg)

    monkeypatch.setattr(Path, "replace", fail_replace)

    with pytest.raises(OSError, match="Simulated atomic replacement failure"):
        write_atomic(summary_path, _NEW_SUMMARY)

    # Existing summary remains undamaged
    assert summary_path.read_text(encoding="utf-8") == _ORIGINAL_SUMMARY
    # Temporary files are cleaned up
    tmp_files = list(tmp_path.glob("*.tmp"))
    assert tmp_files == []
