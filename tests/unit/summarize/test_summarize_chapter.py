import pytest

from src.summarize.pipeline import summarize_chapter
from src.summarize.settings import SummarySettings


@pytest.mark.requirement("REQ-2026-003-F03")
@pytest.mark.parametrize(
    ("rounds", "expected_calls"),
    [
        (0, 1),
        (1, 2),
        (3, 4),
    ],
)
def test_sum_u14_summarize_chapter_invokes_run_for_draft_and_density_rounds(
    rounds: int,
    expected_calls: int,
) -> None:
    """SUM-U14: summarize_chapter executes 1 + density_rounds iterations and strips trailing whitespace."""
    recorded_prompts: list[str] = []

    def fake_run(prompt: str) -> str:
        recorded_prompts.append(prompt)
        return f"\n  要約ラウンド {len(recorded_prompts)} の本文です。  \n"

    settings = SummarySettings(density_rounds=rounds)
    result = summarize_chapter("第1章", "本文サンプル", settings, fake_run)

    assert len(recorded_prompts) == expected_calls
    assert result == f"要約ラウンド {expected_calls} の本文です。"
