from pathlib import Path

import pytest

from src.summarize.pipeline import run
from src.summarize.prompts import draft_prompt, target_chars
from src.summarize.settings import SummarySettings
from src.txt2speech.errors import InputError

_SMALL_BODY = "短い本文です。"
_LARGE_BODY_CHARS = 4000
_BYTES_PER_JAPANESE_CHAR = 3
_PROMPT_LIMIT_BYTES = 3000
_RECORDING_COMMAND = ("fake-llm",)


@pytest.mark.requirement("REQ-2026-003-F07")
def test_oversized_later_chapter_fails_before_any_llm_call(tmp_path: Path) -> None:
    """The pre-run check covers every selected chapter, so chapter 1 is not summarized first."""
    assert _LARGE_BODY_CHARS * _BYTES_PER_JAPANESE_CHAR > _PROMPT_LIMIT_BYTES
    input_path = tmp_path / "book.txt"
    input_path.write_text(
        f"第1章\n{_SMALL_BODY}\n\n第2章\n{'あ' * _LARGE_BODY_CHARS}\n", encoding="utf-8"
    )
    settings = SummarySettings(llm_command=_RECORDING_COMMAND, max_prompt_bytes=_PROMPT_LIMIT_BYTES)
    calls: list[str] = []

    def fake_llm(_settings: SummarySettings, prompt: str) -> str:
        calls.append(prompt)
        return "要約"

    with pytest.raises(InputError, match="第2章"):
        run(input_path, tmp_path / "out", settings, run_llm=fake_llm)

    assert calls == []


@pytest.mark.requirement("REQ-2026-003-F07")
def test_rewrite_prompt_estimate_is_checked_before_any_llm_call(tmp_path: Path) -> None:
    """A chapter whose draft fits but whose rewrite prompt (summary at 2x target) cannot fails early."""
    body = "あ" * _LARGE_BODY_CHARS
    input_path = tmp_path / "book.txt"
    input_path.write_text(f"第1章\n{body}\n", encoding="utf-8")
    base = SummarySettings(llm_command=_RECORDING_COMMAND)
    target = target_chars(body, base)
    draft_bytes = len(draft_prompt("第1章", body, target).encode("utf-8"))
    command_bytes = sum(len(arg.encode("utf-8")) for arg in _RECORDING_COMMAND)
    settings = SummarySettings(
        llm_command=_RECORDING_COMMAND, max_prompt_bytes=command_bytes + draft_bytes
    )
    calls: list[str] = []

    def fake_llm(_settings: SummarySettings, prompt: str) -> str:
        calls.append(prompt)
        return "要約"

    with pytest.raises(InputError, match="第1章"):
        run(input_path, tmp_path / "out", settings, run_llm=fake_llm)

    assert calls == []
