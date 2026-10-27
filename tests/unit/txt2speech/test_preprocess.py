import pytest

from src.txt2speech.preprocess import normalize


@pytest.mark.requirement("REQ-2026-002-F02")
def test_normalize_ruby() -> None:
    """T2S-U01: normalize converts Aozora, Markdown, and HTML ruby to readings."""
    assert normalize("漢字《かんじ》") == "かんじ"
    assert normalize("私《わたし》") == "わたし"
    assert normalize("|ひらがな《かな》") == "かな"
    assert normalize("ひらがな《かな》") == "ひらがな《かな》"
    assert normalize("[漢字](かんじ)") == "かんじ"
    assert normalize("[リンク](https://x.example)") == "[リンク](https://x.example)"
    assert normalize("<ruby>漢字<rt>かんじ</rt></ruby>") == "かんじ"
    assert normalize("<ruby>漢<rp>(</rp><rt>かん</rt><rp>)</rp></ruby>") == "かん"


@pytest.mark.requirement("REQ-2026-002-F02")
def test_normalize_page_and_separator_lines() -> None:
    """T2S-U02: normalize removes page labels, page-number-only lines, and separators."""
    raw = "--- 124 ページ ---\n124\n-----\n本文の行"
    assert normalize(raw) == "本文の行"
    assert normalize("--- 124 ページ ---") == ""
    assert normalize("124") == ""
    assert normalize("-----") == ""


@pytest.mark.requirement("REQ-2026-002-F02")
def test_normalize_figure_references() -> None:
    """T2S-U03: normalize removes figure/table/photo/note markers and collapses spaces."""
    assert normalize("図1-1 を見よ") == "を見よ"
    assert normalize("詳細は 図1-1 を見よ") == "詳細は を見よ"
    assert normalize("表2-3") == ""
    assert normalize("[写真]") == ""
    assert normalize("※注釈です") == ""
    assert normalize("図") == "図"
    assert normalize("写真1-1") == "写真1-1"
    assert normalize("図表3") == "図"


@pytest.mark.requirement("REQ-2026-002-F02")
def test_normalize_readings_and_numbers() -> None:
    """T2S-U04: normalize applies the reading table and strips digit group commas."""
    assert normalize("CO2") == "シーオーツー"
    assert normalize("km/h") == "キロメートル毎時"
    assert normalize("pH") == "ペーハー"
    assert normalize("5%") == "5パーセント"
    assert normalize("1,000") == "1000"
    assert normalize("12,345,678") == "12345678"


@pytest.mark.requirement("REQ-2026-002-F02")
def test_normalize_bullet_lists() -> None:
    """T2S-U05: normalize strips bullet prefixes and ensures sentence-ending punctuation."""
    assert normalize("- 項目") == "項目。"
    assert normalize("・項目。") == "項目。"
    assert normalize("① 項目") == "項目。"
    assert normalize("1) 項目") == "項目。"
    assert normalize("* 項目！") == "項目！"


@pytest.mark.requirement("REQ-2026-002-F02")
def test_normalize_markdown_decorations() -> None:
    """T2S-U06: normalize strips Markdown headings, emphasis, inline code, and quotes."""
    assert normalize("# 見出し") == "見出し"
    assert normalize("**強調**") == "強調"
    assert normalize("`code`") == "code"
    assert normalize("> 引用") == "引用"


@pytest.mark.requirement("REQ-2026-002-F02")
def test_normalize_blank_lines_and_whitespace() -> None:
    """T2S-U07: normalize collapses 3+ newlines to 2 and strips outer whitespace."""
    raw = "  \n\n段落1\n\n\n段落2\n\n\n\n段落3  \n"
    assert normalize(raw) == "段落1\n\n段落2\n\n段落3"
