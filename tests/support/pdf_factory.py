from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.pdfgen import canvas

FONT_NAME = "HeiseiKakuGo-W5"
BODY_SIZE_PT = 10.0
FOOTNOTE_SIZE_PT = 7.5
LEFT_MARGIN_PT = 72.0
PARAGRAPH_INDENT_PT = 82.0
LEADING_PT = 18.0
TOP_Y_PT = 720.0
FOOTNOTE_Y_PT = 72.0
PAGE_NUMBER_Y_PT = 40.0
HEADER_Y_PT = 780.0

pdfmetrics.registerFont(UnicodeCIDFont(FONT_NAME))


@dataclass(frozen=True)
class Line:
    text: str
    x: float = LEFT_MARGIN_PT
    y: float = TOP_Y_PT
    size: float = BODY_SIZE_PT


def body_line(
    text: str,
    line_index: int = 0,
    *,
    indent: bool = False,
    top_y: float = TOP_Y_PT,
) -> Line:
    x = PARAGRAPH_INDENT_PT if indent else LEFT_MARGIN_PT
    y = top_y - line_index * LEADING_PT
    return Line(text=text, x=x, y=y, size=BODY_SIZE_PT)


def body_paragraph(
    lines: Sequence[str],
    start_line_index: int = 0,
    *,
    indent_first: bool = True,
    top_y: float = TOP_Y_PT,
) -> list[Line]:
    return [
        body_line(
            text=text,
            line_index=start_line_index + offset,
            indent=(indent_first and offset == 0),
            top_y=top_y,
        )
        for offset, text in enumerate(lines)
    ]


def footnote_line(
    text: str,
    y: float = FOOTNOTE_Y_PT,
    x: float = LEFT_MARGIN_PT,
) -> Line:
    return Line(text=text, x=x, y=y, size=FOOTNOTE_SIZE_PT)


def page_number_line(
    page_number: int | str,
    y: float = PAGE_NUMBER_Y_PT,
    x: float = LEFT_MARGIN_PT,
) -> Line:
    return Line(text=str(page_number), x=x, y=y, size=BODY_SIZE_PT)


def header_line(
    text: str,
    y: float = HEADER_Y_PT,
    x: float = LEFT_MARGIN_PT,
) -> Line:
    return Line(text=text, x=x, y=y, size=BODY_SIZE_PT)


def build_pdf(
    path: Path,
    pages: Sequence[Sequence[Line]],
    outline: Sequence[tuple[int, str, int]] = (),
    title: str | None = None,
    *,
    encrypt: str | None = None,
) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    pdf_canvas = (
        canvas.Canvas(str(path), encrypt=encrypt)
        if encrypt is not None
        else canvas.Canvas(str(path))
    )
    pdf_canvas.setTitle(title if title is not None else "")

    for page_num, page_lines in enumerate(pages, start=1):
        for idx, (level, entry_title, entry_page) in enumerate(outline):
            if entry_page == page_num:
                key = f"bm_{idx}"
                pdf_canvas.bookmarkPage(key)
                pdf_canvas.addOutlineEntry(entry_title, key, max(0, level - 1))
        for line in page_lines:
            pdf_canvas.setFont(FONT_NAME, line.size)
            pdf_canvas.drawString(line.x, line.y, line.text)
        pdf_canvas.showPage()

    pdf_canvas.save()
    return path
