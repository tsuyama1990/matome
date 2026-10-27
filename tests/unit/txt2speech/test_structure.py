import pytest

from src.txt2speech.models import Chapter
from src.txt2speech.structure import chapter_filename, split_chapters


@pytest.mark.requirement("REQ-2026-002-F04")
def test_split_chapters_headings_and_fallbacks() -> None:
    """T2S-U08: split_chapters splits on headings, ignores '1.' bullets, and handles preambles."""
    md_text = "# 第1章 はじめに\n本文\n## 第2節\n本文"
    assert split_chapters(md_text) == [
        Chapter(title="第1章 はじめに", body="本文"),
        Chapter(title="第2節", body="本文"),
    ]

    jp_text = "第1章 序論\n序論の本文\n第2節 方法\n方法の本文"
    assert split_chapters(jp_text) == [
        Chapter(title="第1章 序論", body="序論の本文"),
        Chapter(title="第2節 方法", body="方法の本文"),
    ]

    num_text = "1.1 概要\n概要の本文\n1.2 方法\n方法の本文"
    assert split_chapters(num_text) == [
        Chapter(title="1.1 概要", body="概要の本文"),
        Chapter(title="1.2 方法", body="方法の本文"),
    ]

    bullet_text = "1. 箇条書きの項目\n2. 次の項目"
    assert split_chapters(bullet_text) == [Chapter(title="", body=bullet_text)]

    no_heading_text = "見出しのない本文です。"
    assert split_chapters(no_heading_text) == [Chapter(title="", body=no_heading_text)]

    preamble_text = "先頭の本文\n# 第1章 本編\n本編の本文"
    assert split_chapters(preamble_text) == [
        Chapter(title="", body="先頭の本文"),
        Chapter(title="第1章 本編", body="本編の本文"),
    ]


@pytest.mark.requirement("REQ-2026-002-F04")
def test_split_chapters_empty_chapters_and_blank_input() -> None:
    """T2S-U09: split_chapters skips chapters with empty bodies and returns [] for blank input."""
    with_empty_chapter = "# 第1章\n   \n# 第2章\n本文あり\n# 第3章"
    assert split_chapters(with_empty_chapter) == [
        Chapter(title="第2章", body="本文あり"),
    ]

    assert split_chapters("   \n\n\t  ") == []
    assert split_chapters("") == []


@pytest.mark.requirement("REQ-2026-002-F04")
def test_chapter_filename() -> None:
    """T2S-U10: chapter_filename formats indices, sanitizes forbidden chars, and caps length."""
    assert chapter_filename(1, "第1章", 2) == "01_第1章.mp3"
    assert chapter_filename(3, "a/b:c", 2) == "03_a_b_c.mp3"
    assert chapter_filename(1, "", 2) == "01.mp3"

    long_title = "あ" * 100
    assert chapter_filename(1, long_title, 2) == f"01_{'あ' * 80}.mp3"

    total_chapters = 100
    width = max(2, len(str(total_chapters)))
    assert width == 3
    assert chapter_filename(1, "第1章", width) == "001_第1章.mp3"
