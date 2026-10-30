import pytest

from src.txt2speech.chapters import select_chapters
from src.txt2speech.errors import InputError
from src.txt2speech.models import Chapter

_CHAPTERS = [
    Chapter(title="第1章", body="本文1"),
    Chapter(title="第2章", body="本文2"),
    Chapter(title="第3章", body="本文3"),
    Chapter(title="第4章", body="本文4"),
]


@pytest.mark.requirement("REQ-2026-003-F01")
@pytest.mark.parametrize(
    ("spec", "expected_indices"),
    [
        (None, [1, 2, 3, 4]),
        ("2", [2]),
        ("2-3", [2, 3]),
        ("2-", [2, 3, 4]),
        ("-2", [1, 2]),
    ],
)
def test_sum_u16_select_chapters_ranges(spec: str | None, expected_indices: list[int]) -> None:
    """SUM-U16: select_chapters selects 1-based chapters according to spec matching txt2speech."""
    selected = select_chapters(_CHAPTERS, spec)
    assert [idx for idx, _ch in selected] == expected_indices


@pytest.mark.requirement("REQ-2026-003-F01")
def test_sum_u16_select_chapters_raises_input_error_when_out_of_range() -> None:
    """SUM-U16: select_chapters raises InputError when specified range contains no chapters."""
    with pytest.raises(InputError, match="指定した範囲に章がありません"):
        select_chapters(_CHAPTERS, "5-6")
