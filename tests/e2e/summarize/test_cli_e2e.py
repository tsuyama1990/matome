import json
import os
import subprocess
import sys
import time
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import pytest

from src.summarize.prompts import (
    STYLE_RULES,
    draft_prompt,
    target_chars,
)
from src.summarize.settings import SummarySettings
from src.txt2speech.structure import split_chapters
from tests.support.fake_llm import read_calls, write_fake_llm

_PROJECT_ROOT_DEPTH = 3
_PROJECT_ROOT = Path(__file__).resolve().parents[_PROJECT_ROOT_DEPTH]

_EXIT_OK = 0
_EXIT_INPUT_ERROR = 2
_EXIT_ENGINE_ERROR = 3

_KILL_POLL_TIMEOUT_SECONDS = 3.0
_KILL_POLL_INTERVAL_SECONDS = 0.05
_SHORT_RETRY_WAIT_SECONDS = 0.01
_SHORT_TIMEOUT_SECONDS = 0.2

_TWO_CHAPTERS_TEXT = "# 第1章 序論\n第1章の本文です。\n\n# 第2章 本論\n第2章の本文です。\n"
_THREE_CHAPTERS_TEXT = (
    "# 第1章 序論\n第1章本文\n\n# 第2章 本論\n第2章本文\n\n# 第3章 結論\n第3章本文\n"
)


def _run_summarize_cli(
    args: Sequence[str],
    extra_env: Mapping[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    if extra_env is not None:
        env.update(extra_env)
    cmd = [sys.executable, "-m", "src.summarize", *args]
    return subprocess.run(  # noqa: S603
        cmd,
        cwd=_PROJECT_ROOT,
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )


def _write_config_json(
    path: Path,
    *,
    llm_command: Sequence[str],
    llm_retry_wait_seconds: float = _SHORT_RETRY_WAIT_SECONDS,
    **kwargs: Any,
) -> Path:
    config_dict = {
        "llm_command": list(llm_command),
        "llm_retry_wait_seconds": llm_retry_wait_seconds,
        **kwargs,
    }
    path.write_text(json.dumps(config_dict, ensure_ascii=False), encoding="utf-8")
    return path


@pytest.mark.requirement("REQ-2026-003-F05")
@pytest.mark.requirement("REQ-2026-003-F08")
def test_sum_e01_markdown_summary_and_stdout_path(tmp_path: Path) -> None:
    """SUM-E01: CLI generates summary.md for 2 chapters with exit code 0 and prints summary path."""
    input_path = tmp_path / "book.txt"
    input_path.write_text(_TWO_CHAPTERS_TEXT, encoding="utf-8")
    out_dir = tmp_path / "out"

    cmd, _log = write_fake_llm(tmp_path, replies=["第1章の要約", "第2章の要約"])
    cfg_path = _write_config_json(tmp_path / "config.json", llm_command=cmd)

    proc = _run_summarize_cli([str(input_path), "-o", str(out_dir), "--config", str(cfg_path)])

    assert proc.returncode == _EXIT_OK
    expected_summary_path = out_dir / "summary.md"
    assert proc.stdout.strip() == str(expected_summary_path)
    assert expected_summary_path.is_file()

    summary_content = expected_summary_path.read_text(encoding="utf-8")
    assert "# 第1章 序論" in summary_content
    assert "# 第2章 本論" in summary_content


@pytest.mark.requirement("REQ-2026-003-F02")
def test_sum_e02_prompt_records_approximate_300_chars_for_1000_char_body(tmp_path: Path) -> None:
    """SUM-E02: 1,000-character body records approximately 300 characters in prompt."""
    input_path = tmp_path / "book.txt"
    input_path.write_text("# 第1章 序論\n" + "あ" * 1000 + "\n", encoding="utf-8")
    out_dir = tmp_path / "out"

    cmd, log = write_fake_llm(tmp_path)
    cfg_path = _write_config_json(
        tmp_path / "config.json",
        llm_command=cmd,
        summary_ratio=0.2,
        summary_min_chars=300,
    )

    proc = _run_summarize_cli([str(input_path), "-o", str(out_dir), "--config", str(cfg_path)])
    assert proc.returncode == _EXIT_OK

    calls = read_calls(log)
    assert len(calls) >= 1
    assert "約300字" in calls[0]["prompt"]


@pytest.mark.requirement("REQ-2026-003-F03")
def test_sum_e03_density_rounds_two_executes_three_llm_calls_in_sequence(tmp_path: Path) -> None:
    """SUM-E03: density_rounds=2 produces 3 calls with iterative summaries and final output in summary.md."""
    input_path = tmp_path / "book.txt"
    input_path.write_text("# 第1章 序論\n本文テキストです。\n", encoding="utf-8")
    out_dir = tmp_path / "out"

    cmd, log = write_fake_llm(
        tmp_path,
        replies=["初回ドラフト要約", "第1回書き直し要約", "第2回最終要約"],
    )
    cfg_path = _write_config_json(
        tmp_path / "config.json",
        llm_command=cmd,
        density_rounds=2,
    )

    proc = _run_summarize_cli([str(input_path), "-o", str(out_dir), "--config", str(cfg_path)])
    assert proc.returncode == _EXIT_OK

    calls = read_calls(log)
    assert len(calls) == 3
    assert "本文テキストです。" in calls[1]["prompt"]
    assert "初回ドラフト要約" in calls[1]["prompt"]
    assert "本文テキストです。" in calls[2]["prompt"]
    assert "第1回書き直し要約" in calls[2]["prompt"]

    summary_content = (out_dir / "summary.md").read_text(encoding="utf-8")
    assert "第2回最終要約" in summary_content


@pytest.mark.requirement("REQ-2026-003-F04")
def test_sum_e04_first_prompt_contains_all_f04_style_rules(tmp_path: Path) -> None:
    """SUM-E04: first LLM prompt contains all style rule constraints from REQ-2026-003-F04."""
    input_path = tmp_path / "book.txt"
    input_path.write_text("# 第1章 序論\n本文テキストです。\n", encoding="utf-8")
    out_dir = tmp_path / "out"

    cmd, log = write_fake_llm(tmp_path)
    cfg_path = _write_config_json(tmp_path / "config.json", llm_command=cmd)

    proc = _run_summarize_cli([str(input_path), "-o", str(out_dir), "--config", str(cfg_path)])
    assert proc.returncode == _EXIT_OK

    calls = read_calls(log)
    assert len(calls) >= 1
    first_prompt = calls[0]["prompt"]
    for rule in STYLE_RULES:
        assert rule in first_prompt


@pytest.mark.requirement("REQ-2026-003-F06")
def test_sum_e05_second_run_reuses_cached_results_without_additional_llm_calls(
    tmp_path: Path,
) -> None:
    """SUM-E05: executing identical input and config twice does not trigger additional LLM calls."""
    input_path = tmp_path / "book.txt"
    input_path.write_text("# 第1章 序論\n本文テキストです。\n", encoding="utf-8")
    out_dir = tmp_path / "out"

    cmd, log = write_fake_llm(tmp_path)
    cfg_path = _write_config_json(tmp_path / "config.json", llm_command=cmd)

    proc1 = _run_summarize_cli([str(input_path), "-o", str(out_dir), "--config", str(cfg_path)])
    assert proc1.returncode == _EXIT_OK
    calls_after_run1 = len(read_calls(log))
    assert calls_after_run1 > 0
    content1 = (out_dir / "summary.md").read_text(encoding="utf-8")

    proc2 = _run_summarize_cli([str(input_path), "-o", str(out_dir), "--config", str(cfg_path)])
    assert proc2.returncode == _EXIT_OK
    calls_after_run2 = len(read_calls(log))
    assert calls_after_run2 == calls_after_run1
    content2 = (out_dir / "summary.md").read_text(encoding="utf-8")
    assert content1 == content2


@pytest.mark.requirement("REQ-2026-003-F06")
def test_sum_e06_changing_summary_ratio_triggers_recomputation(tmp_path: Path) -> None:
    """SUM-E06: modifying summary_ratio invalidates cache and triggers new LLM calls."""
    input_path = tmp_path / "book.txt"
    input_path.write_text("# 第1章 序論\n" + "あ" * 2000 + "\n", encoding="utf-8")
    out_dir = tmp_path / "out"

    cmd, log = write_fake_llm(tmp_path)
    cfg_path1 = _write_config_json(tmp_path / "config1.json", llm_command=cmd, summary_ratio=0.2)
    proc1 = _run_summarize_cli([str(input_path), "-o", str(out_dir), "--config", str(cfg_path1)])
    assert proc1.returncode == _EXIT_OK
    calls_after_run1 = len(read_calls(log))

    cfg_path2 = _write_config_json(tmp_path / "config2.json", llm_command=cmd, summary_ratio=0.5)
    proc2 = _run_summarize_cli([str(input_path), "-o", str(out_dir), "--config", str(cfg_path2)])
    assert proc2.returncode == _EXIT_OK
    calls_after_run2 = len(read_calls(log))
    assert calls_after_run2 > calls_after_run1


@pytest.mark.requirement("REQ-2026-003-F07")
def test_sum_e07_precheck_prompt_size_exceeded_fails_with_exit_code_2(tmp_path: Path) -> None:
    """SUM-E07: oversized prompt pre-check fails with exit code 2, prints title, zero LLM calls."""
    input_path = tmp_path / "book.txt"
    input_path.write_text("# 第1章 巨大な本文\n" + "あ" * 40_000 + "\n", encoding="utf-8")
    out_dir = tmp_path / "out"

    cmd, log = write_fake_llm(tmp_path)
    cfg_path = _write_config_json(tmp_path / "config.json", llm_command=cmd)

    proc = _run_summarize_cli([str(input_path), "-o", str(out_dir), "--config", str(cfg_path)])
    assert proc.returncode == _EXIT_INPUT_ERROR
    assert "第1章 巨大な本文" in proc.stderr
    assert read_calls(log) == []
    assert not (out_dir / "summary.md").exists()


@pytest.mark.requirement("REQ-2026-003-F07")
def test_sum_e08_second_chapter_llm_failure_aborts_with_exit_code_3(tmp_path: Path) -> None:
    """SUM-E08: LLM failure on chapter 2 exits with code 3, prints chapter title, preserves chapter 1 cache."""
    input_path = tmp_path / "book.txt"
    input_path.write_text(_TWO_CHAPTERS_TEXT, encoding="utf-8")
    out_dir = tmp_path / "out"

    cmd, _log = write_fake_llm(tmp_path, fail_when="第2章 本論")
    cfg_path = _write_config_json(tmp_path / "config.json", llm_command=cmd, llm_retries=1)

    proc = _run_summarize_cli([str(input_path), "-o", str(out_dir), "--config", str(cfg_path)])
    assert proc.returncode == _EXIT_ENGINE_ERROR
    assert "第2章 本論" in proc.stderr
    assert not (out_dir / "summary.md").exists()

    work_dir = out_dir / ".summarize_work"
    assert list(work_dir.glob("01_*.txt"))


@pytest.mark.requirement("REQ-2026-003-F01")
def test_sum_e09_chapters_flag_selects_only_specified_chapter(tmp_path: Path) -> None:
    """SUM-E09: --chapters 2 filters input to summarize only the second chapter."""
    input_path = tmp_path / "book.txt"
    input_path.write_text(_THREE_CHAPTERS_TEXT, encoding="utf-8")
    out_dir = tmp_path / "out"

    cmd, _log = write_fake_llm(tmp_path)
    cfg_path = _write_config_json(tmp_path / "config.json", llm_command=cmd)

    proc = _run_summarize_cli(
        [str(input_path), "-o", str(out_dir), "--config", str(cfg_path), "--chapters", "2"]
    )
    assert proc.returncode == _EXIT_OK

    summary = (out_dir / "summary.md").read_text(encoding="utf-8")
    assert "# 第2章 本論" in summary
    assert "# 第1章 序論" not in summary
    assert "# 第3章 結論" not in summary


@pytest.mark.requirement("REQ-2026-003-F08")
def test_sum_e10_unknown_config_key_fails_with_exit_code_2(tmp_path: Path) -> None:
    """SUM-E10: unknown configuration key causes exit code 2 and outputs key name to stderr."""
    input_path = tmp_path / "book.txt"
    input_path.write_text(_TWO_CHAPTERS_TEXT, encoding="utf-8")
    out_dir = tmp_path / "out"

    cmd, _log = write_fake_llm(tmp_path)
    cfg_path = _write_config_json(
        tmp_path / "config.json",
        llm_command=cmd,
        unknown_super_key="invalid_value",
    )

    proc = _run_summarize_cli([str(input_path), "-o", str(out_dir), "--config", str(cfg_path)])
    assert proc.returncode == _EXIT_INPUT_ERROR
    assert "unknown_super_key" in proc.stderr


@pytest.mark.requirement("REQ-2026-003-F09")
def test_sum_e11_first_stderr_line_announces_llm_command_head(tmp_path: Path) -> None:
    """SUM-E11: first line of stderr explicitly states target of data transmission."""
    input_path = tmp_path / "book.txt"
    input_path.write_text("# 第1章 序論\n本文テキスト\n", encoding="utf-8")
    out_dir = tmp_path / "out"

    cmd, _log = write_fake_llm(tmp_path)
    cfg_path = _write_config_json(tmp_path / "config.json", llm_command=cmd)

    proc = _run_summarize_cli([str(input_path), "-o", str(out_dir), "--config", str(cfg_path)])
    assert proc.returncode == _EXIT_OK

    first_stderr_line = proc.stderr.splitlines()[0]
    assert cmd[0] in first_stderr_line
    assert "本文を" in first_stderr_line
    assert "に送ります" in first_stderr_line


@pytest.mark.requirement("REQ-2026-003-F08")
def test_sum_e13_nonexistent_input_file_fails_with_exit_code_2(tmp_path: Path) -> None:
    """SUM-E13: nonexistent input path exits with code 2 and reports missing path."""
    missing_file = tmp_path / "nonexistent_input_book.txt"
    out_dir = tmp_path / "out"

    cmd, _log = write_fake_llm(tmp_path)
    cfg_path = _write_config_json(tmp_path / "config.json", llm_command=cmd)

    proc = _run_summarize_cli([str(missing_file), "-o", str(out_dir), "--config", str(cfg_path)])
    assert proc.returncode == _EXIT_INPUT_ERROR
    assert missing_file.name in proc.stderr


@pytest.mark.requirement("REQ-2026-003-F02")
def test_sum_e14_approximate_target_chars_caps_at_short_body_length(tmp_path: Path) -> None:
    """SUM-E14: 100-character body records approximately 100 characters in prompt."""
    input_path = tmp_path / "book.txt"
    input_path.write_text("# 第1章 序論\n" + "あ" * 100 + "\n", encoding="utf-8")
    out_dir = tmp_path / "out"

    cmd, log = write_fake_llm(tmp_path)
    cfg_path = _write_config_json(
        tmp_path / "config.json",
        llm_command=cmd,
        summary_min_chars=300,
    )

    proc = _run_summarize_cli([str(input_path), "-o", str(out_dir), "--config", str(cfg_path)])
    assert proc.returncode == _EXIT_OK

    calls = read_calls(log)
    assert len(calls) >= 1
    assert "約100字" in calls[0]["prompt"]


@pytest.mark.requirement("REQ-2026-003-F05")
@pytest.mark.requirement("REQ-2026-003-F07")
def test_sum_e15_failed_execution_preserves_existing_summary_md(tmp_path: Path) -> None:
    """SUM-E15: failed re-execution leaves pre-existing summary.md unmodified."""
    input_path = tmp_path / "book.txt"
    input_path.write_text(_TWO_CHAPTERS_TEXT, encoding="utf-8")
    out_dir = tmp_path / "out"

    # Step 1: initial successful execution
    cmd_ok, _log = write_fake_llm(
        tmp_path,
        config_name="cfg_ok.json",
        log_name="ok.log",
        replies=["要約1", "要約2"],
    )
    cfg_ok = _write_config_json(tmp_path / "config_ok.json", llm_command=cmd_ok)
    proc1 = _run_summarize_cli([str(input_path), "-o", str(out_dir), "--config", str(cfg_ok)])
    assert proc1.returncode == _EXIT_OK
    original_summary = (out_dir / "summary.md").read_text(encoding="utf-8")

    # Step 2: second execution with different ratio and failing LLM
    cmd_fail, _log_fail = write_fake_llm(
        tmp_path,
        config_name="cfg_fail.json",
        log_name="fail.log",
        exit_code=1,
    )
    cfg_fail = _write_config_json(
        tmp_path / "config_fail.json",
        llm_command=cmd_fail,
        summary_ratio=0.5,
        llm_retries=0,
    )
    proc2 = _run_summarize_cli([str(input_path), "-o", str(out_dir), "--config", str(cfg_fail)])
    assert proc2.returncode == _EXIT_ENGINE_ERROR

    current_summary = (out_dir / "summary.md").read_text(encoding="utf-8")
    assert current_summary == original_summary


@pytest.mark.requirement("REQ-2026-003-F05")
def test_sum_e16_summary_headings_stripped_preserves_chapter_count(tmp_path: Path) -> None:
    """SUM-E16: summary lines starting with '#' do not corrupt txt2speech chapter splitting."""
    input_path = tmp_path / "book.txt"
    input_path.write_text("# 第1章 序論\n本文テキスト\n", encoding="utf-8")
    out_dir = tmp_path / "out"

    cmd, _log = write_fake_llm(
        tmp_path,
        replies=["# 見出し行1\n本文行\n## 見出し行2\n本文行"],
    )
    cfg_path = _write_config_json(tmp_path / "config.json", llm_command=cmd)

    proc = _run_summarize_cli([str(input_path), "-o", str(out_dir), "--config", str(cfg_path)])
    assert proc.returncode == _EXIT_OK

    summary_content = (out_dir / "summary.md").read_text(encoding="utf-8")
    chapters = split_chapters(summary_content)
    assert len(chapters) == 1
    assert chapters[0].title == "第1章 序論"


@pytest.mark.requirement("REQ-2026-003-F07")
def test_sum_e17_first_call_huge_summary_exceeds_rewrite_size_limit(tmp_path: Path) -> None:
    """SUM-E17: oversized actual rewrite prompt aborts with exit code 2 and exactly 1 LLM call."""
    input_path = tmp_path / "book.txt"
    input_path.write_text("# 第1章 序論\n本文テキスト\n", encoding="utf-8")
    out_dir = tmp_path / "out"

    # Pre-check size calculation
    temp_settings = SummarySettings(density_rounds=1)
    target = target_chars("本文テキスト", temp_settings)
    draft = draft_prompt("第1章 序論", "本文テキスト", target)
    draft_size = sum(len(a.encode("utf-8")) for a in (*temp_settings.llm_command, draft))
    max_bytes = draft_size + 3000

    cmd, log = write_fake_llm(tmp_path, replies=["巨大な要約文です。" * 1000])
    cfg_path = _write_config_json(
        tmp_path / "config.json",
        llm_command=cmd,
        density_rounds=1,
        max_prompt_bytes=max_bytes,
    )

    proc = _run_summarize_cli([str(input_path), "-o", str(out_dir), "--config", str(cfg_path)])
    assert proc.returncode == _EXIT_INPUT_ERROR
    assert "第1章 序論" in proc.stderr
    assert len(read_calls(log)) == 1


@pytest.mark.requirement("REQ-2026-003-F07")
def test_sum_e18_child_process_killed_on_timeout(tmp_path: Path) -> None:
    """SUM-E18: LLM child process group is terminated upon timeout without orphaned processes."""
    input_path = tmp_path / "book.txt"
    input_path.write_text("# 第1章 序論\n本文テキスト\n", encoding="utf-8")
    out_dir = tmp_path / "out"

    child_pid_file = tmp_path / "grandchild.pid"
    cmd, _log = write_fake_llm(tmp_path, child_pid_file=str(child_pid_file))
    cfg_path = _write_config_json(
        tmp_path / "config.json",
        llm_command=cmd,
        llm_retries=0,
        llm_timeout_seconds=_SHORT_TIMEOUT_SECONDS,
    )

    proc = _run_summarize_cli([str(input_path), "-o", str(out_dir), "--config", str(cfg_path)])
    assert proc.returncode == _EXIT_ENGINE_ERROR

    assert child_pid_file.is_file()
    child_pid = int(child_pid_file.read_text(encoding="utf-8").strip())

    deadline = time.monotonic() + _KILL_POLL_TIMEOUT_SECONDS
    child_dead = False
    while time.monotonic() < deadline:
        try:
            os.kill(child_pid, 0)
        except ProcessLookupError:
            child_dead = True
            break
        time.sleep(_KILL_POLL_INTERVAL_SECONDS)

    assert child_dead, f"Child process {child_pid} remained active"


@pytest.mark.requirement("REQ-2026-003-F08")
def test_sum_e19_progress_reported_to_stderr_for_two_chapters(tmp_path: Path) -> None:
    """SUM-E19: stderr contains '要約 1/2' and '要約 2/2' progress lines."""
    input_path = tmp_path / "book.txt"
    input_path.write_text(_TWO_CHAPTERS_TEXT, encoding="utf-8")
    out_dir = tmp_path / "out"

    cmd, _log = write_fake_llm(tmp_path)
    cfg_path = _write_config_json(tmp_path / "config.json", llm_command=cmd)

    proc = _run_summarize_cli([str(input_path), "-o", str(out_dir), "--config", str(cfg_path)])
    assert proc.returncode == _EXIT_OK

    assert "要約 1/2: 第1章 序論" in proc.stderr
    assert "要約 2/2: 第2章 本論" in proc.stderr


@pytest.mark.requirement("REQ-2026-003-F08")
def test_sum_e20_command_line_chapters_flag_overrides_config_file(tmp_path: Path) -> None:
    """SUM-E20: CLI --chapters flag overrides chapters setting in configuration file."""
    input_path = tmp_path / "book.txt"
    input_path.write_text(_THREE_CHAPTERS_TEXT, encoding="utf-8")
    out_dir = tmp_path / "out"

    cmd, _log = write_fake_llm(tmp_path)
    cfg_path = _write_config_json(
        tmp_path / "config.json",
        llm_command=cmd,
        chapters="1",
    )

    proc = _run_summarize_cli(
        [str(input_path), "-o", str(out_dir), "--config", str(cfg_path), "--chapters", "2"]
    )
    assert proc.returncode == _EXIT_OK

    summary = (out_dir / "summary.md").read_text(encoding="utf-8")
    assert "# 第2章 本論" in summary
    assert "# 第1章 序論" not in summary
