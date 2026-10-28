import pytest

from src.txt2speech.config import Settings, load_settings
from src.txt2speech.errors import InputError
from src.txt2speech.pdf_input import (
    ChapterSpan,
    LineRecord,
    OutlineEntry,
    assemble_paragraphs,
    clean_title,
    drop_noise,
    find_repeated_texts,
    median_body_size,
    select_chapters,
    strip_note_markers,
)

_BODY_SIZE = 10.0
_FOOTNOTE_SIZE = 7.5
_LEFT_MARGIN = 72.0
_INDENT_X = 82.0
_LEADING = 18.0
_TOP_Y = 700.0


@pytest.mark.requirement("REQ-2026-002-F12")
def test_clean_title() -> None:
    """T2S-U22: clean_title strips garbage tails, collapses CJK spaces, and keeps ASCII word spaces."""
    assert (
        clean_title("第 1 章 structure - conduct - performance ( SCP ) theory , IO theory")
        == "第1章structure-conduct-performance(SCP)theory,IO theory"
    )
    assert clean_title("序章 経営 理論 とは 何 か") == "序章経営理論とは何か"
    assert (
        clean_title(
            "第 7 章 transaction cost theory 取引 費用 理論 （ TCE \uff00\u2000\u3100\u3000"
        )
        == "第7章transaction cost theory取引費用理論（TCE"
    )
    assert (
        clean_title("『 世界標準 の 経営 理論 』 を 手 にさ れ た 方 へ")
        == "『世界標準の経営理論』を手にされた方へ"
    )
    assert clean_title("Part 1") == "Part 1"
    assert clean_title("\ufffd壊れた") == ""
    assert clean_title("") == ""
    assert clean_title("第 1 章 (") == "第1章"
    assert clean_title("第 2 章 （") == "第2章"


@pytest.mark.requirement("REQ-2026-002-F13")
def test_drop_noise() -> None:
    """T2S-U23: drop_noise removes footnotes, digit-only lines, and repeated headers/footers."""
    settings = Settings()
    lines: list[LineRecord] = []
    for page_num in range(1, 11):
        lines.append(
            LineRecord(
                page=page_num,
                text=f"ページ{page_num}の本文です。",
                x0=_LEFT_MARGIN,
                y0=_TOP_Y,
                size=_BODY_SIZE,
            )
        )
        if page_num <= 5:
            lines.append(
                LineRecord(
                    page=page_num,
                    text="繰り返すヘッダー",
                    x0=_LEFT_MARGIN,
                    y0=780.0,
                    size=_BODY_SIZE,
                )
            )
        if page_num <= 2:
            lines.append(
                LineRecord(
                    page=page_num,
                    text="2ページだけの行",
                    x0=_LEFT_MARGIN,
                    y0=660.0,
                    size=_BODY_SIZE,
                )
            )

    lines.extend(
        [
            LineRecord(
                page=1,
                text="注１：これは脚注の本文です。",
                x0=_LEFT_MARGIN,
                y0=72.0,
                size=_FOOTNOTE_SIZE,
            ),
            LineRecord(page=1, text="124", x0=_LEFT_MARGIN, y0=40.0, size=_BODY_SIZE),
            LineRecord(page=2, text="１２５", x0=_LEFT_MARGIN, y0=40.0, size=_BODY_SIZE),
        ]
    )

    body_size = median_body_size(lines)
    repeated = find_repeated_texts(lines, settings, total_pages=10)
    assert repeated == {"繰り返すヘッダー"}

    kept = drop_noise(lines, body_size, repeated, settings)
    kept_texts = [line.text for line in kept]

    assert "注１：これは脚注の本文です。" not in kept_texts
    assert "124" not in kept_texts
    assert "１２５" not in kept_texts
    assert "繰り返すヘッダー" not in kept_texts
    assert kept_texts.count("2ページだけの行") == 2
    assert "ページ1の本文です。" in kept_texts

    # When page count is below pdf_repeat_min_pages (default 3), repeat filtering is skipped.
    two_page_lines = [
        LineRecord(page=1, text="共通ヘッダー", x0=_LEFT_MARGIN, y0=780.0, size=_BODY_SIZE),
        LineRecord(page=1, text="一ページ目の本文。", x0=_LEFT_MARGIN, y0=_TOP_Y, size=_BODY_SIZE),
        LineRecord(page=2, text="共通ヘッダー", x0=_LEFT_MARGIN, y0=780.0, size=_BODY_SIZE),
        LineRecord(page=2, text="二ページ目の本文。", x0=_LEFT_MARGIN, y0=_TOP_Y, size=_BODY_SIZE),
    ]
    assert find_repeated_texts(two_page_lines, settings, total_pages=2) == set()
    kept_two_page = drop_noise(two_page_lines, settings)
    assert [line.text for line in kept_two_page].count("共通ヘッダー") == 2


@pytest.mark.requirement("REQ-2026-002-F13")
def test_assemble_paragraphs_wrapped_indented_heading_and_english() -> None:
    """T2S-U24: assemble_paragraphs joins wrapped lines, splits on indent/wide gap, and spaces English."""
    settings = Settings()

    # 3 wrapped Japanese lines become 1 sentence without spaces.
    wrapped_jp = [
        LineRecord(page=1, text="これは折り返された", x0=_LEFT_MARGIN, y0=700.0, size=_BODY_SIZE),
        LineRecord(page=1, text="三行にわたる日本語の", x0=_LEFT_MARGIN, y0=682.0, size=_BODY_SIZE),
        LineRecord(page=1, text="一つの文です。", x0=_LEFT_MARGIN, y0=664.0, size=_BODY_SIZE),
    ]
    assert assemble_paragraphs(wrapped_jp, settings) == (
        "これは折り返された三行にわたる日本語の一つの文です。"
    )

    # 2 indented paragraphs separated by a blank line.
    indented_two = [
        LineRecord(page=1, text="最初の段落の一行目と", x0=_INDENT_X, y0=700.0, size=_BODY_SIZE),
        LineRecord(
            page=1, text="折り返しの二行目です。", x0=_LEFT_MARGIN, y0=682.0, size=_BODY_SIZE
        ),
        LineRecord(page=1, text="次の段落の一行目と", x0=_INDENT_X, y0=664.0, size=_BODY_SIZE),
        LineRecord(
            page=1, text="折り返しの二行目です。", x0=_LEFT_MARGIN, y0=646.0, size=_BODY_SIZE
        ),
    ]
    assert assemble_paragraphs(indented_two, settings) == (
        "最初の段落の一行目と折り返しの二行目です。\n\n次の段落の一行目と折り返しの二行目です。"
    )

    # A short heading line with wide vertical gaps before and after becomes its own paragraph.
    with_heading = [
        LineRecord(page=1, text="前の段落の一行目と", x0=_LEFT_MARGIN, y0=700.0, size=_BODY_SIZE),
        LineRecord(page=1, text="二行目の文です。", x0=_LEFT_MARGIN, y0=682.0, size=_BODY_SIZE),
        LineRecord(page=1, text="第1節 見出し", x0=_LEFT_MARGIN, y0=640.0, size=_BODY_SIZE),
        LineRecord(page=1, text="後の段落の一行目と", x0=_LEFT_MARGIN, y0=598.0, size=_BODY_SIZE),
        LineRecord(page=1, text="二行目と", x0=_LEFT_MARGIN, y0=580.0, size=_BODY_SIZE),
        LineRecord(page=1, text="三行目の文です。", x0=_LEFT_MARGIN, y0=562.0, size=_BODY_SIZE),
    ]
    assert assemble_paragraphs(with_heading, settings) == (
        "前の段落の一行目と二行目の文です。\n\n第1節 見出し\n\n後の段落の一行目と二行目と三行目の文です。"
    )

    # English alphanumeric words across wrapped lines are joined with a single space.
    english_lines = [
        LineRecord(page=1, text="This is competitive", x0=_LEFT_MARGIN, y0=700.0, size=_BODY_SIZE),
        LineRecord(
            page=1, text="strategy in practice.", x0=_LEFT_MARGIN, y0=682.0, size=_BODY_SIZE
        ),
    ]
    assert (
        assemble_paragraphs(english_lines, settings) == "This is competitive strategy in practice."
    )


@pytest.mark.requirement("REQ-2026-002-F13")
def test_assemble_paragraphs_across_pages() -> None:
    """T2S-U24: assemble_paragraphs joins cross-page sentences unless the next page starts indented."""
    settings = Settings()

    # Cross-page continuation (no sentence-end punctuation on page 1, unindented first line on page 2).
    cross_page_joined = [
        LineRecord(page=1, text="ページをまたいで続く", x0=_LEFT_MARGIN, y0=100.0, size=_BODY_SIZE),
        LineRecord(page=2, text="一つの文です。", x0=_LEFT_MARGIN, y0=700.0, size=_BODY_SIZE),
    ]
    assert assemble_paragraphs(cross_page_joined, settings) == "ページをまたいで続く一つの文です。"

    # Cross-page where the next page's first line is indented starts a new paragraph.
    cross_page_indented = [
        LineRecord(page=1, text="前のページの途中", x0=_LEFT_MARGIN, y0=100.0, size=_BODY_SIZE),
        LineRecord(
            page=2,
            text="字下げされた新しい段落です。",
            x0=_INDENT_X,
            y0=700.0,
            size=_BODY_SIZE,
        ),
        LineRecord(
            page=2, text="二ページ目の続きです。", x0=_LEFT_MARGIN, y0=682.0, size=_BODY_SIZE
        ),
    ]
    assert assemble_paragraphs(cross_page_indented, settings) == (
        "前のページの途中\n\n字下げされた新しい段落です。二ページ目の続きです。"
    )


@pytest.mark.requirement("REQ-2026-002-F13")
def test_strip_note_markers() -> None:
    """T2S-U25: strip_note_markers removes inline footnote markers without touching normal words."""
    assert strip_note_markers("使う注１。") == "使う。"
    assert strip_note_markers("注意が必要だ") == "注意が必要だ"
    assert strip_note_markers("注文を受ける") == "注文を受ける"
    assert strip_note_markers("注１、注２") == "、"
    assert strip_note_markers("参照注１") == "参照"
    assert strip_note_markers("注の付いた語") == "注の付いた語"


@pytest.mark.requirement("REQ-2026-002-F12")
def test_select_chapters() -> None:
    """T2S-U26: select_chapters filters by level, orders by page, deduplicates same-page, and sets spans."""
    # 1-level outline.
    one_level = [
        OutlineEntry(level=1, title="第1章", page=2),
        OutlineEntry(level=1, title="第2章", page=5),
    ]
    assert select_chapters(one_level, max_level=1, last_page=8) == [
        ChapterSpan(title="第1章", start_page=2, end_page=4),
        ChapterSpan(title="第2章", start_page=5, end_page=8),
    ]

    # 2-level outline with max_level=1 vs max_level=2.
    two_level = [
        OutlineEntry(level=1, title="第1章", page=2),
        OutlineEntry(level=2, title="第1節", page=3),
        OutlineEntry(level=1, title="第2章", page=6),
    ]
    assert select_chapters(two_level, max_level=1, last_page=9) == [
        ChapterSpan(title="第1章", start_page=2, end_page=5),
        ChapterSpan(title="第2章", start_page=6, end_page=9),
    ]
    assert select_chapters(two_level, max_level=2, last_page=9) == [
        ChapterSpan(title="第1章", start_page=2, end_page=2),
        ChapterSpan(title="第1節", start_page=3, end_page=5),
        ChapterSpan(title="第2章", start_page=6, end_page=9),
    ]

    # Same page entries keep the later one; reversed order is sorted by page; last spans to last_page.
    same_page_and_reversed = [
        OutlineEntry(level=1, title="第2章", page=6),
        OutlineEntry(level=1, title="第1部", page=2),
        OutlineEntry(level=1, title="第1章", page=2),
    ]
    assert select_chapters(same_page_and_reversed, max_level=1, last_page=10) == [
        ChapterSpan(title="第1章", start_page=2, end_page=5),
        ChapterSpan(title="第2章", start_page=6, end_page=10),
    ]


@pytest.mark.requirement("REQ-2026-002-F12")
@pytest.mark.requirement("REQ-2026-002-F13")
def test_pdf_settings_validation() -> None:
    """T2S-U22: load_settings validates the six pdf_* settings fields."""
    valid = load_settings(
        None,
        {
            "pdf_outline_level": 2,
            "pdf_footnote_size_ratio": 0.8,
            "pdf_repeat_page_ratio": 0.5,
            "pdf_repeat_min_pages": 4,
            "pdf_indent_tolerance_pt": 4.0,
            "pdf_paragraph_gap_ratio": 1.5,
        },
    )
    assert valid.pdf_outline_level == 2

    with pytest.raises(InputError):
        load_settings(None, {"pdf_outline_level": 0})
    with pytest.raises(InputError):
        load_settings(None, {"pdf_footnote_size_ratio": 0.0})
    with pytest.raises(InputError):
        load_settings(None, {"pdf_footnote_size_ratio": 1.1})
    with pytest.raises(InputError):
        load_settings(None, {"pdf_repeat_page_ratio": 0.0})
    with pytest.raises(InputError):
        load_settings(None, {"pdf_repeat_page_ratio": 1.2})
    with pytest.raises(InputError):
        load_settings(None, {"pdf_repeat_min_pages": 1})
    with pytest.raises(InputError):
        load_settings(None, {"pdf_indent_tolerance_pt": 0.0})
    with pytest.raises(InputError):
        load_settings(None, {"pdf_paragraph_gap_ratio": 0.0})
