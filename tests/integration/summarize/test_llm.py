import os
import time
from pathlib import Path

import pytest

from src.summarize.llm import run_llm
from src.summarize.settings import SummarySettings
from src.txt2speech.errors import EngineError
from tests.support.fake_llm import read_calls, write_fake_llm

_SHORT_RETRY_WAIT_SECONDS = 0.01
_KILL_POLL_TIMEOUT_SECONDS = 3.0
_KILL_POLL_INTERVAL_SECONDS = 0.05
_SHORT_TIMEOUT_SECONDS = 0.2


@pytest.mark.requirement("REQ-2026-003-F03")
def test_sum_i01_run_llm_preserves_trailing_whitespace(tmp_path: Path) -> None:
    """SUM-I01: run_llm returns exact stdout from fake LLM without stripping whitespace."""
    cmd, _log = write_fake_llm(tmp_path, echo=True)
    settings = SummarySettings(llm_command=cmd)
    prompt = "  前後空白と改行を含むプロンプト  \n"

    result = run_llm(settings, prompt)
    assert result == prompt


@pytest.mark.requirement("REQ-2026-003-F03")
def test_sum_i02_run_llm_passes_special_characters_intact(tmp_path: Path) -> None:
    """SUM-I02: run_llm passes Japanese, newlines, quotes, $, and backticks without modification."""
    cmd, log = write_fake_llm(tmp_path, echo=True)
    settings = SummarySettings(llm_command=cmd)
    prompt = "日本語改行テスト\n\"二重引用符\"と'単一引用符'、$SHELL_VAR、`backtick`、\\円マーク"

    result = run_llm(settings, prompt)
    assert result == prompt

    calls = read_calls(log)
    assert len(calls) == 1
    assert calls[0]["prompt"] == prompt


@pytest.mark.requirement("REQ-2026-003-F07")
def test_sum_i03_run_llm_retries_and_exponential_backoff(tmp_path: Path) -> None:
    """SUM-I03: run_llm succeeds on 3rd attempt with sleeps matching 2.0s and 4.0s."""
    cmd, log = write_fake_llm(
        tmp_path,
        fail_calls=[1, 2],
        replies=["失敗1", "失敗2", "成功した応答"],
    )
    recorded_sleeps: list[float] = []
    settings = SummarySettings(
        llm_command=cmd,
        llm_retries=2,
        llm_retry_wait_seconds=2.0,
    )

    result = run_llm(settings, "プロンプト", sleep=recorded_sleeps.append)
    assert result == "成功した応答"
    assert len(read_calls(log)) == 3
    assert recorded_sleeps == [2.0, 4.0]


@pytest.mark.requirement("REQ-2026-003-F07")
def test_sum_i04_run_llm_empty_stdout_retries_and_raises_engine_error(tmp_path: Path) -> None:
    """SUM-I04: run_llm treats empty stdout as failure and exhausts retries to raise EngineError."""
    cmd, log = write_fake_llm(tmp_path, replies=["   \n\t  "])
    settings = SummarySettings(
        llm_command=cmd,
        llm_retries=1,
        llm_retry_wait_seconds=_SHORT_RETRY_WAIT_SECONDS,
    )

    with pytest.raises(EngineError, match="標準出力が空です"):
        run_llm(settings, "プロンプト")

    assert len(read_calls(log)) == 2


@pytest.mark.requirement("REQ-2026-003-F07")
def test_sum_i05_run_llm_timeout_retries_and_raises_engine_error(tmp_path: Path) -> None:
    """SUM-I05: run_llm terminates timed-out process and raises EngineError after retries."""
    cmd, log = write_fake_llm(tmp_path, sleep=5.0)
    settings = SummarySettings(
        llm_command=cmd,
        llm_retries=1,
        llm_timeout_seconds=0.1,
        llm_retry_wait_seconds=_SHORT_RETRY_WAIT_SECONDS,
    )

    with pytest.raises(EngineError, match="タイムアウト"):
        run_llm(settings, "プロンプト")

    assert len(read_calls(log)) == 2


@pytest.mark.requirement("REQ-2026-003-F07")
def test_sum_i06_run_llm_missing_command_fails_without_retries() -> None:
    """SUM-I06: run_llm fails immediately with EngineError and zero sleeps if command not found."""
    nonexistent_cmd = ("/nonexistent_dir/nonexistent_llm_command_xyz",)
    recorded_sleeps: list[float] = []
    settings = SummarySettings(llm_command=nonexistent_cmd, llm_retries=2)

    with pytest.raises(EngineError, match=nonexistent_cmd[0]):
        run_llm(settings, "プロンプト", sleep=recorded_sleeps.append)

    assert recorded_sleeps == []


@pytest.mark.requirement("REQ-2026-003-F07")
def test_sum_i07_run_llm_retries_zero_fails_on_first_attempt(tmp_path: Path) -> None:
    """SUM-I07: run_llm with llm_retries=0 executes exactly once before raising EngineError."""
    cmd, log = write_fake_llm(tmp_path, fail_calls=[1])
    settings = SummarySettings(llm_command=cmd, llm_retries=0)

    with pytest.raises(EngineError):
        run_llm(settings, "プロンプト")

    assert len(read_calls(log)) == 1


@pytest.mark.requirement("REQ-2026-003-F07")
def test_sum_i15_run_llm_non_utf8_stdout_retries_and_fails(tmp_path: Path) -> None:
    """SUM-I15: run_llm retries upon encountering invalid UTF-8 bytes in stdout."""
    # Invalid UTF-8 start byte
    cmd, log = write_fake_llm(tmp_path, raw_hex="fffe00")
    settings = SummarySettings(
        llm_command=cmd,
        llm_retries=1,
        llm_retry_wait_seconds=_SHORT_RETRY_WAIT_SECONDS,
    )

    with pytest.raises(EngineError, match="標準出力が UTF-8 として読めません"):
        run_llm(settings, "プロンプト")

    assert len(read_calls(log)) == 2


@pytest.mark.requirement("REQ-2026-003-F07")
def test_sum_i16_run_llm_kills_child_process_group_on_timeout(tmp_path: Path) -> None:
    """SUM-I16: run_llm terminates background child processes created by LLM on timeout."""
    child_pid_file = tmp_path / "grandchild.pid"
    cmd, _log = write_fake_llm(tmp_path, child_pid_file=str(child_pid_file))
    settings = SummarySettings(
        llm_command=cmd,
        llm_retries=0,
        llm_timeout_seconds=_SHORT_TIMEOUT_SECONDS,
    )

    with pytest.raises(EngineError, match="タイムアウト"):
        run_llm(settings, "プロンプト")

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

    assert child_dead, f"Child process {child_pid} was not terminated"
