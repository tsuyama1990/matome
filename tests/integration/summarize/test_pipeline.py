from pathlib import Path

import pytest

from src.summarize import pipeline
from src.summarize.prompts import (
    CURRENT_SEPARATOR,
    draft_prompt,
    target_chars,
)
from src.summarize.settings import SummarySettings
from src.txt2speech.errors import EngineError, InputError

_TWO_CHAPTER_TEXT = "# 第1章 序論\n第1章の本文です。\n\n# 第2章 本論\n第2章の本文です。\n"


@pytest.mark.requirement("REQ-2026-003-F03")
def test_sum_i10_pipeline_run_invokes_draft_then_density_rounds(tmp_path: Path) -> None:
    """SUM-I10: pipeline.run executes 1 + density_rounds calls per chapter in order."""
    input_file = tmp_path / "input.txt"
    input_file.write_text(_TWO_CHAPTER_TEXT, encoding="utf-8")
    out_dir = tmp_path / "out"

    calls: list[str] = []

    def fake_runner(_settings: SummarySettings, prompt: str) -> str:
        calls.append(prompt)
        return f"要約結果 {len(calls)}"

    settings = SummarySettings(density_rounds=1)
    summary_path = pipeline.run(input_file, out_dir, settings, run_llm=fake_runner)

    assert summary_path.is_file()
    # 2 chapters * (1 draft + 1 rewrite) = 4 calls
    assert len(calls) == 4

    # Chapter 1: draft then rewrite
    assert CURRENT_SEPARATOR not in calls[0]
    assert CURRENT_SEPARATOR in calls[1]
    # Chapter 2: draft then rewrite
    assert CURRENT_SEPARATOR not in calls[2]
    assert CURRENT_SEPARATOR in calls[3]


@pytest.mark.requirement("REQ-2026-003-F06")
def test_sum_i11_pipeline_run_reuses_cached_summaries_on_second_run(tmp_path: Path) -> None:
    """SUM-I11: pipeline.run reuses cached results on second execution with zero LLM calls."""
    input_file = tmp_path / "input.txt"
    input_file.write_text(_TWO_CHAPTER_TEXT, encoding="utf-8")
    out_dir = tmp_path / "out"

    first_calls: list[str] = []

    def initial_runner(_settings: SummarySettings, prompt: str) -> str:
        first_calls.append(prompt)
        return f"キャッシュ用要約 {len(first_calls)}"

    settings = SummarySettings(density_rounds=1)
    path1 = pipeline.run(input_file, out_dir, settings, run_llm=initial_runner)
    content1 = path1.read_text(encoding="utf-8")
    assert len(first_calls) == 4

    second_calls: list[str] = []

    def cached_runner(_settings: SummarySettings, prompt: str) -> str:
        second_calls.append(prompt)
        return "新しく生成された要約"

    path2 = pipeline.run(input_file, out_dir, settings, run_llm=cached_runner)
    content2 = path2.read_text(encoding="utf-8")

    assert len(second_calls) == 0
    assert content1 == content2


@pytest.mark.requirement("REQ-2026-003-F07")
def test_sum_i12_pipeline_run_preserves_first_chapter_cache_on_second_chapter_failure(
    tmp_path: Path,
) -> None:
    """SUM-I12: pipeline.run failure in second chapter leaves first chapter cached and omits summary.md."""
    input_file = tmp_path / "input.txt"
    input_file.write_text(_TWO_CHAPTER_TEXT, encoding="utf-8")
    out_dir = tmp_path / "out"

    def fail_on_chapter2(_settings: SummarySettings, prompt: str) -> str:
        if "第2章 本論" in prompt:
            msg = "LLM failed on chapter 2"
            raise EngineError(msg)
        return "第1章の完成要約"

    settings = SummarySettings(density_rounds=0)
    with pytest.raises(EngineError, match="第2章 本論"):
        pipeline.run(input_file, out_dir, settings, run_llm=fail_on_chapter2)

    # summary.md must not exist
    assert not (out_dir / pipeline.SUMMARY_FILE_NAME).exists()

    # First chapter cache file must exist in .summarize_work
    work_dir = out_dir / pipeline.WORK_DIR_NAME
    cached_chapter1 = list(work_dir.glob("01_*.txt"))
    assert len(cached_chapter1) == 1
    assert cached_chapter1[0].read_text(encoding="utf-8") == "第1章の完成要約"


@pytest.mark.requirement("REQ-2026-003-F07")
def test_sum_i17_pipeline_run_oversized_actual_rewrite_aborts_without_second_call(
    tmp_path: Path,
) -> None:
    """SUM-I17: oversized actual rewrite prompt raises InputError before second LLM call."""
    input_file = tmp_path / "input.txt"
    input_file.write_text("# 第1章 序論\n短い本文です。\n", encoding="utf-8")
    out_dir = tmp_path / "out"

    # Pre-check size with estimate (estimate = 2 * target = 600 chars of 'あ')
    base_settings = SummarySettings(density_rounds=1)
    target = target_chars("短い本文です。", base_settings)
    draft = draft_prompt("第1章 序論", "短い本文です。", target)
    draft_size = sum(len(a.encode("utf-8")) for a in (*base_settings.llm_command, draft))

    # Allow draft and estimated rewrite to pass pre-check, but fail when actual output is huge
    max_bytes = draft_size + 3000
    settings = SummarySettings(density_rounds=1, max_prompt_bytes=max_bytes)

    calls: list[str] = []

    def huge_first_reply(_settings: SummarySettings, prompt: str) -> str:
        calls.append(prompt)
        # Return overwhelmingly large summary (e.g. 5000 chars of 3-byte Japanese = ~15,000 bytes)
        return "巨大な要約本文です。" * 1000

    with pytest.raises(InputError, match="第1章 序論"):
        pipeline.run(input_file, out_dir, settings, run_llm=huge_first_reply)

    assert len(calls) == 1


@pytest.mark.requirement("REQ-2026-003-F07")
def test_sum_i18_pipeline_run_density_rounds_zero_bypasses_rewrite_size_check(
    tmp_path: Path,
) -> None:
    """SUM-I18: density_rounds=0 skips rewrite size check, succeeding with single call."""
    input_file = tmp_path / "input.txt"
    input_file.write_text("# 第1章 序論\n本文テキスト。\n", encoding="utf-8")
    out_dir = tmp_path / "out"

    # Compute size of draft
    temp_settings = SummarySettings(density_rounds=0)
    target = target_chars("本文テキスト。", temp_settings)
    draft = draft_prompt("第1章 序論", "本文テキスト。", target)
    draft_size = sum(len(a.encode("utf-8")) for a in (*temp_settings.llm_command, draft))

    # Set max_prompt_bytes just enough for draft, but not enough for estimated rewrite
    settings = SummarySettings(density_rounds=0, max_prompt_bytes=draft_size + 50)

    calls: list[str] = []

    def single_runner(_settings: SummarySettings, prompt: str) -> str:
        calls.append(prompt)
        return "単一ラウンドの要約です。"

    summary_path = pipeline.run(input_file, out_dir, settings, run_llm=single_runner)
    assert summary_path.is_file()
    assert len(calls) == 1


@pytest.mark.requirement("REQ-2026-003-F01")
def test_pipeline_run_raises_input_error_when_no_chapters_found(tmp_path: Path) -> None:
    """InputError is raised when input file has zero chapters."""
    empty_file = tmp_path / "empty.txt"
    empty_file.write_text("", encoding="utf-8")
    out_dir = tmp_path / "out"

    with pytest.raises(InputError, match="要約する章がありません"):
        pipeline.run(empty_file, out_dir, SummarySettings())


@pytest.mark.requirement("REQ-2026-003-F08")
def test_pipeline_run_notifies_progress_callback_for_each_chapter(tmp_path: Path) -> None:
    """Progress callback receives (position, total, title) for each chapter."""
    input_file = tmp_path / "input.txt"
    input_file.write_text(_TWO_CHAPTER_TEXT, encoding="utf-8")
    out_dir = tmp_path / "out"

    progress_events: list[tuple[int, int, str]] = []

    def record_progress(pos: int, total: int, title: str) -> None:
        progress_events.append((pos, total, title))

    def dummy_runner(_settings: SummarySettings, _prompt: str) -> str:
        return "進捗テスト用要約"

    settings = SummarySettings(density_rounds=0)
    pipeline.run(
        input_file,
        out_dir,
        settings,
        run_llm=dummy_runner,
        progress_cb=record_progress,
    )

    assert progress_events == [
        (1, 2, "第1章 序論"),
        (2, 2, "第2章 本論"),
    ]
