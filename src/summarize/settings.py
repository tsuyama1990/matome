from collections.abc import Mapping
from dataclasses import dataclass, fields
from pathlib import Path
from typing import Any

from src.txt2speech.config import normalize_chapters, parse_chapter_range, read_yaml
from src.txt2speech.errors import InputError

DEFAULT_LLM_COMMAND = (
    "agy-cli",
    "--model",
    "Gemini 4 Argon (High)",
    "--print-timeout",
    "600s",
    "-p",
)
DEFAULT_SUMMARY_RATIO = 0.2
DEFAULT_SUMMARY_MIN_CHARS = 300
DEFAULT_DENSITY_ROUNDS = 1
DEFAULT_LLM_RETRIES = 2
DEFAULT_LLM_RETRY_WAIT_SECONDS = 2.0
DEFAULT_LLM_TIMEOUT_SECONDS = 900.0
DEFAULT_MAX_PROMPT_BYTES = 100_000


@dataclass(frozen=True)
class SummarySettings:
    llm_command: tuple[str, ...] = DEFAULT_LLM_COMMAND
    summary_ratio: float = DEFAULT_SUMMARY_RATIO
    summary_min_chars: int = DEFAULT_SUMMARY_MIN_CHARS
    density_rounds: int = DEFAULT_DENSITY_ROUNDS
    llm_retries: int = DEFAULT_LLM_RETRIES
    llm_retry_wait_seconds: float = DEFAULT_LLM_RETRY_WAIT_SECONDS
    llm_timeout_seconds: float = DEFAULT_LLM_TIMEOUT_SECONDS
    max_prompt_bytes: int = DEFAULT_MAX_PROMPT_BYTES
    chapters: str | None = None


def _is_int(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _is_number(value: object) -> bool:
    return isinstance(value, int | float) and not isinstance(value, bool)


def _require(ok: bool, key: str, rule: str) -> None:
    if not ok:
        msg = f"{key} は{rule}である必要があります"
        raise InputError(msg)


def _normalize_command(raw: object) -> tuple[str, ...]:
    if not isinstance(raw, list | tuple) or not raw:
        msg = "llm_command は空でない文字列の並びである必要があります"
        raise InputError(msg)
    if not all(isinstance(item, str) and item for item in raw):
        msg = "llm_command の要素は空でない文字列である必要があります"
        raise InputError(msg)
    return tuple(raw)


def _validate(settings: SummarySettings) -> None:
    ratio = settings.summary_ratio
    _require(_is_number(ratio) and 0 < ratio <= 1, "summary_ratio", "0 より大きく 1 以下の数")
    min_chars = settings.summary_min_chars
    _require(_is_int(min_chars) and min_chars >= 1, "summary_min_chars", "1 以上の整数")
    rounds = settings.density_rounds
    _require(_is_int(rounds) and rounds >= 0, "density_rounds", "0 以上の整数")
    retries = settings.llm_retries
    _require(_is_int(retries) and retries >= 0, "llm_retries", "0 以上の整数")
    wait = settings.llm_retry_wait_seconds
    _require(_is_number(wait) and wait > 0, "llm_retry_wait_seconds", "0 より大きい数")
    timeout = settings.llm_timeout_seconds
    _require(_is_number(timeout) and timeout > 0, "llm_timeout_seconds", "0 より大きい数")
    max_bytes = settings.max_prompt_bytes
    _require(_is_int(max_bytes) and max_bytes >= 1, "max_prompt_bytes", "1 以上の整数")
    if settings.chapters is not None:
        parse_chapter_range(settings.chapters)


def load_summary_settings(
    path: Path | None = None,
    overrides: Mapping[str, object] | None = None,
) -> SummarySettings:
    merged: dict[str, Any] = read_yaml(path) if path is not None else {}
    if overrides is not None:
        merged.update(overrides)
    unknown_keys = set(merged) - {f.name for f in fields(SummarySettings)}
    if unknown_keys:
        msg = f"未知の設定キーが含まれています: {sorted(unknown_keys)}"
        raise InputError(msg)
    if "llm_command" in merged:
        merged["llm_command"] = _normalize_command(merged["llm_command"])
    if "chapters" in merged:
        merged["chapters"] = normalize_chapters(merged["chapters"])
    settings = SummarySettings(**merged)
    _validate(settings)
    return settings
