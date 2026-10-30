from pathlib import Path

import pytest

from src.txt2speech.chapters import load_chapters
from src.txt2speech.config import Settings
from tests.support.pdf_factory import Line, body_paragraph, build_pdf

_SAMPLE_TEXT = (
    "# 第1章 テキスト\nテキストの第1章本文です。\n\n# 第2章 テキスト\nテキストの第2章本文です。\n"
)
_SAMPLE_MD = "# 第1章 マークダウン\nマークダウンの第1章本文です。\n\n# 第2章 マークダウン\nマークダウンの第2章本文です。\n"


@pytest.mark.requirement("REQ-2026-003-F01")
def test_sum_i13_load_chapters_supports_pdf_text_and_markdown(tmp_path: Path) -> None:
    """SUM-I13: load_chapters extracts identical chapter structure for PDF, text, and markdown."""
    settings = Settings()

    # 1. Plain text (.txt)
    txt_path = tmp_path / "sample.txt"
    txt_path.write_text(_SAMPLE_TEXT, encoding="utf-8")
    txt_chapters = load_chapters(txt_path, settings)
    assert len(txt_chapters) == 2
    assert txt_chapters[0].title == "第1章 テキスト"
    assert "テキストの第1章本文です。" in txt_chapters[0].body
    assert txt_chapters[1].title == "第2章 テキスト"
    assert "テキストの第2章本文です。" in txt_chapters[1].body

    # 2. Markdown (.md)
    md_path = tmp_path / "sample.md"
    md_path.write_text(_SAMPLE_MD, encoding="utf-8")
    md_chapters = load_chapters(md_path, settings)
    assert len(md_chapters) == 2
    assert md_chapters[0].title == "第1章 マークダウン"
    assert "マークダウンの第1章本文です。" in md_chapters[0].body
    assert md_chapters[1].title == "第2章 マークダウン"
    assert "マークダウンの第2章本文です。" in md_chapters[1].body

    # 3. PDF (.pdf)
    pdf_path = tmp_path / "sample.pdf"
    pages: list[list[Line]] = [
        [*body_paragraph(["PDFの一章本文です。"])],
        [*body_paragraph(["PDFの二章本文です。"])],
    ]
    outline = [
        (1, "第 1 章", 1),
        (1, "第 2 章", 2),
    ]
    build_pdf(pdf_path, pages=pages, outline=outline)
    pdf_chapters = load_chapters(pdf_path, settings)
    assert len(pdf_chapters) == 2
    assert pdf_chapters[0].title == "第1章"
    assert "PDFの一章本文です。" in pdf_chapters[0].body
    assert pdf_chapters[1].title == "第2章"
    assert "PDFの二章本文です。" in pdf_chapters[1].body
