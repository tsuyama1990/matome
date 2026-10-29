from pathlib import Path

import pytest

from src.summarize.prompts import (
    DENSITY_TEMPLATE,
    draft_prompt,
    target_chars,
)
from src.summarize.settings import SummarySettings
from src.summarize.store import _entry_path, cache_key, render
from src.txt2speech.structure import split_chapters

_BASE_TITLE = "第1章 基礎概念"
_BASE_BODY = "基礎概念の本文です。" * 200
_ALT_TITLE = "第2章 応用概念"
_ALT_BODY = "別の章の本文です。" * 200
_CUSTOM_DENSITY_TEMPLATE = DENSITY_TEMPLATE + "\n追加指示"


@pytest.mark.requirement("REQ-2026-003-F06")
def test_sum_u06_cache_key_sensitivity_and_invariance() -> None:
    """SUM-U06: cache_key changes for 8 distinct variations and stays invariant for retries/timeout."""
    base_settings = SummarySettings()
    base_target = target_chars(_BASE_BODY, base_settings)
    base_draft = draft_prompt(_BASE_TITLE, _BASE_BODY, base_target)
    base_key = cache_key(base_draft, DENSITY_TEMPLATE, base_settings)

    # Identical input produces identical key
    assert cache_key(base_draft, DENSITY_TEMPLATE, base_settings) == base_key

    # 1: title change
    draft_alt_title = draft_prompt(_ALT_TITLE, _BASE_BODY, base_target)
    assert cache_key(draft_alt_title, DENSITY_TEMPLATE, base_settings) != base_key

    # 2: body change
    draft_alt_body = draft_prompt(_BASE_TITLE, _ALT_BODY, base_target)
    assert cache_key(draft_alt_body, DENSITY_TEMPLATE, base_settings) != base_key

    # 3: ratio change
    ratio_settings = SummarySettings(summary_ratio=0.5)
    target_ratio = target_chars(_BASE_BODY, ratio_settings)
    assert target_ratio != base_target
    draft_ratio = draft_prompt(_BASE_TITLE, _BASE_BODY, target_ratio)
    assert cache_key(draft_ratio, DENSITY_TEMPLATE, base_settings) != base_key

    # 4: min_chars change
    min_settings = SummarySettings(summary_min_chars=500)
    target_min = target_chars(_BASE_BODY, min_settings)
    assert target_min != base_target
    draft_min = draft_prompt(_BASE_TITLE, _BASE_BODY, target_min)
    assert cache_key(draft_min, DENSITY_TEMPLATE, base_settings) != base_key

    # 5: rounds change
    rounds_settings = SummarySettings(density_rounds=2)
    assert cache_key(base_draft, DENSITY_TEMPLATE, rounds_settings) != base_key

    # 6: command change
    cmd_settings = SummarySettings(llm_command=("custom-cli", "-p"))
    assert cache_key(base_draft, DENSITY_TEMPLATE, cmd_settings) != base_key

    # 7: style rules change in draft prompt
    draft_alt_style = base_draft.replace("本文に書かれている内容だけを使い", "自由な発想で補い")
    assert cache_key(draft_alt_style, DENSITY_TEMPLATE, base_settings) != base_key

    # 8: density template change
    assert cache_key(base_draft, _CUSTOM_DENSITY_TEMPLATE, base_settings) != base_key

    # Invariant: changing retries, timeout, retry wait, max_prompt_bytes, or chapters does not affect key
    invariant_settings = SummarySettings(
        llm_retries=5,
        llm_retry_wait_seconds=10.0,
        llm_timeout_seconds=30.0,
        max_prompt_bytes=50_000,
        chapters="1-2",
    )
    assert cache_key(base_draft, DENSITY_TEMPLATE, invariant_settings) == base_key


@pytest.mark.requirement("REQ-2026-003-F06")
def test_sum_u07_entry_path_formats_two_digit_index_and_key() -> None:
    """SUM-U07: _entry_path generates filename 06_abc.txt for index 6 and key abc."""
    work_dir = Path("/sample/work")
    expected = work_dir / "06_abc.txt"
    assert _entry_path(work_dir, 6, "abc") == expected


@pytest.mark.requirement("REQ-2026-003-F05")
def test_sum_u08_render_formats_two_chapters() -> None:
    """SUM-U08: render formats two chapters with single trailing newline."""
    items = [("題1", "要約1"), ("題2", "要約2")]
    expected = "# 題1\n\n要約1\n\n# 題2\n\n要約2\n"
    assert render(items) == expected


@pytest.mark.requirement("REQ-2026-003-F05")
def test_sum_u17_render_strips_markdown_headings_from_title_and_summary_lines() -> None:
    """SUM-U17: render strips leading hashes from title and summary lines while keeping mid-line hashes."""
    title = "# 第1章\n続き"
    summary = "# 見出し風\n## 二段\n### 三段\n本文 # 途中"
    rendered = render([(title, summary)])
    expected = "# 第1章 続き\n\n見出し風\n二段\n三段\n本文 # 途中\n"
    assert rendered == expected


@pytest.mark.requirement("REQ-2026-003-F05")
def test_sum_u09_render_output_roundtrips_through_txt2speech_split_chapters() -> None:
    """SUM-U09: render output cleanly round-trips through split_chapters with identical titles and bodies."""
    items = [("第1章 はじめに", "1章の要約文です。"), ("第2章 おわりに", "2章の要約文です。")]
    text = render(items)
    chapters = split_chapters(text)

    assert len(chapters) == len(items)
    for chapter, (expected_title, expected_body) in zip(chapters, items, strict=True):
        assert chapter.title == expected_title
        assert chapter.body == expected_body
