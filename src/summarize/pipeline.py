from collections.abc import Callable
from pathlib import Path

from src.summarize import store
from src.summarize.llm import run_llm
from src.summarize.prompts import (
    DENSITY_TEMPLATE,
    check_prompt_size,
    density_prompt,
    draft_prompt,
    target_chars,
)
from src.summarize.settings import SummarySettings
from src.txt2speech.chapters import load_chapters, select_chapters
from src.txt2speech.config import Settings
from src.txt2speech.errors import EngineError, InputError

SUMMARY_FILE_NAME = "summary.md"
WORK_DIR_NAME = ".summarize_work"
# The rewrite prompt is checked before any call, when the current summary is not yet known.
_ESTIMATE_LENGTH_FACTOR = 2
_ESTIMATE_CHAR = "あ"

LlmRunner = Callable[[SummarySettings, str], str]
ProgressCallback = Callable[[int, int, str], None]


def _noop_progress(_position: int, _total: int, _title: str) -> None:
    return None


def summarize_chapter(
    title: str,
    body: str,
    settings: SummarySettings,
    run: Callable[[str], str],
) -> str:
    target = target_chars(body, settings)
    prompts = [draft_prompt(title, body, target)]
    summary = ""
    try:
        for round_index in range(1 + settings.density_rounds):
            if round_index:
                prompts.append(density_prompt(title, body, summary, target))
            check_prompt_size(title, settings, prompts[-1])
            summary = run(prompts[-1]).strip()
    except EngineError as exc:
        msg = f"章「{title}」の要約に失敗しました: {exc}"
        raise EngineError(msg) from exc
    return summary


def _check_all_sizes(
    chapters: list[tuple[int, str, str]],
    settings: SummarySettings,
) -> None:
    for _index, title, body in chapters:
        target = target_chars(body, settings)
        check_prompt_size(title, settings, draft_prompt(title, body, target))
        if settings.density_rounds >= 1:
            estimate = _ESTIMATE_CHAR * (_ESTIMATE_LENGTH_FACTOR * target)
            check_prompt_size(title, settings, density_prompt(title, body, estimate, target))


def run(
    input_path: Path,
    out_dir: Path,
    settings: SummarySettings,
    run_llm: LlmRunner = run_llm,
    progress_cb: ProgressCallback | None = None,
) -> Path:
    selected = select_chapters(load_chapters(input_path, Settings()), settings.chapters)
    if not selected:
        msg = "要約する章がありません"
        raise InputError(msg)
    chapters = [(index, chapter.title, chapter.body) for index, chapter in selected]
    _check_all_sizes(chapters, settings)

    work_dir = out_dir / WORK_DIR_NAME
    active_progress = progress_cb if progress_cb is not None else _noop_progress
    results: list[tuple[str, str]] = []
    for position, (index, title, body) in enumerate(chapters, start=1):
        active_progress(position, len(chapters), title)
        target = target_chars(body, settings)
        key = store.cache_key(draft_prompt(title, body, target), DENSITY_TEMPLATE, settings)
        summary = store.load(work_dir, index, key)
        if summary is None:
            summary = summarize_chapter(
                title, body, settings, lambda prompt: run_llm(settings, prompt)
            )
            store.save(work_dir, index, key, summary)
        results.append((title, summary))

    summary_path = out_dir / SUMMARY_FILE_NAME
    store.write_atomic(summary_path, store.render(results))
    return summary_path
