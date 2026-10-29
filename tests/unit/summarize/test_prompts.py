import pytest

from src.summarize.prompts import (
    BODY_SEPARATOR,
    CURRENT_SEPARATOR,
    STYLE_RULES,
    check_prompt_size,
    density_prompt,
    draft_prompt,
    target_chars,
)
from src.summarize.settings import SummarySettings
from src.txt2speech.errors import InputError

_DEFAULT_SETTINGS = SummarySettings()
_RATIO_ONE_SETTINGS = SummarySettings(summary_ratio=1.0)
_SAMPLE_BODY_1K = "あ" * 1000
_SAMPLE_BODY_10956 = "あ" * 10956
_SAMPLE_BODY_100 = "あ" * 100
_SAMPLE_BODY_200 = "あ" * 200
_SAMPLE_BODY_300 = "あ" * 300
_SAMPLE_BODY_301 = "あ" * 301
_SAMPLE_BODY_40K = "あ" * 40_000

_EXPECTED_1K_TARGET = 300
_EXPECTED_10956_TARGET = 2191
_EXPECTED_100_TARGET = 100
_EXPECTED_200_TARGET = 200
_EXPECTED_300_TARGET = 300
_EXPECTED_301_TARGET = 300
_RULE_COUNT = 6
_LARGE_COMMAND_ARG_LEN = 100_005


@pytest.mark.requirement("REQ-2026-003-F02")
def test_sum_u01_target_chars_calculates_expected_lengths() -> None:
    """SUM-U01: target_chars calculates expected lengths for various body lengths."""
    assert target_chars(_SAMPLE_BODY_1K, _DEFAULT_SETTINGS) == _EXPECTED_1K_TARGET
    assert target_chars(_SAMPLE_BODY_10956, _DEFAULT_SETTINGS) == _EXPECTED_10956_TARGET
    assert target_chars(_SAMPLE_BODY_100, _DEFAULT_SETTINGS) == _EXPECTED_100_TARGET


@pytest.mark.requirement("REQ-2026-003-F02")
def test_sum_u02_target_chars_boundary_conditions() -> None:
    """SUM-U02: target_chars boundary conditions for ratio and min_chars."""
    assert target_chars(_SAMPLE_BODY_200, _RATIO_ONE_SETTINGS) == _EXPECTED_200_TARGET
    assert target_chars(_SAMPLE_BODY_300, _DEFAULT_SETTINGS) == _EXPECTED_300_TARGET
    assert target_chars(_SAMPLE_BODY_301, _DEFAULT_SETTINGS) == _EXPECTED_301_TARGET


@pytest.mark.requirement("REQ-2026-003-F02")
@pytest.mark.requirement("REQ-2026-003-F04")
def test_sum_u03_draft_prompt_contains_rules_target_and_body() -> None:
    """SUM-U03: draft_prompt includes approx target chars, rules, title, and body."""
    title = "第1章 序論"
    body = "これは章の本文です。"
    target = 300
    prompt = draft_prompt(title, body, target)

    assert f"約{target}字" in prompt
    assert title in prompt
    assert BODY_SEPARATOR in prompt

    body_part = prompt.split(BODY_SEPARATOR, 1)[1]
    assert body in body_part

    for rule in STYLE_RULES:
        assert rule in prompt


@pytest.mark.requirement("REQ-2026-003-F03")
def test_sum_u04_density_prompt_contains_current_summary_and_body() -> None:
    """SUM-U04: density_prompt includes current summary before body and retains target."""
    title = "第1章 序論"
    body = "本文テキストです。"
    current = "初回のドラフト要約です。"
    target = 300
    prompt = density_prompt(title, body, current, target)

    assert f"約{target}字" in prompt
    assert CURRENT_SEPARATOR in prompt
    assert BODY_SEPARATOR in prompt

    current_idx = prompt.index(CURRENT_SEPARATOR)
    body_idx = prompt.index(BODY_SEPARATOR)
    assert current_idx < body_idx
    assert current in prompt[current_idx:body_idx]
    assert body in prompt[body_idx:]


@pytest.mark.requirement("REQ-2026-003-F04")
def test_sum_u05_style_rules_contains_six_distinct_rules() -> None:
    """SUM-U05: STYLE_RULES has six separate lines covering all requirements."""
    assert len(STYLE_RULES) == _RULE_COUNT
    assert any("本文に書かれている内容だけを使い" in rule for rule in STYLE_RULES)
    assert any("聞いて分かる話し言葉" in rule for rule in STYLE_RULES)
    assert any("箇条書き・記号・括弧書き・見出し記号" in rule for rule in STYLE_RULES)
    assert any("英語の理論名は初出で日本語の読みを添える" in rule for rule in STYLE_RULES)
    assert any("構成は「この章の問い」" in rule for rule in STYLE_RULES)
    assert any("出力は要約の本文のみ" in rule for rule in STYLE_RULES)


@pytest.mark.requirement("REQ-2026-003-F07")
def test_sum_u15_check_prompt_size_rejects_large_prompt() -> None:
    """SUM-U15: check_prompt_size rejects large prompts counting UTF-8 bytes and llm_command."""
    title_long = "第1章 巨大な本文"
    target = target_chars(_SAMPLE_BODY_40K, _DEFAULT_SETTINGS)
    large_draft = draft_prompt(title_long, _SAMPLE_BODY_40K, target)
    with pytest.raises(InputError, match=title_long):
        check_prompt_size(title_long, _DEFAULT_SETTINGS, large_draft)

    title_args = "第2章 コマンドが長い"
    long_cmd_settings = SummarySettings(
        llm_command=("agy-cli", "x" * _LARGE_COMMAND_ARG_LEN),
        max_prompt_bytes=100_000,
    )
    with pytest.raises(InputError, match=title_args):
        check_prompt_size(title_args, long_cmd_settings, "短いプロンプト")
