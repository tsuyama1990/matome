from collections.abc import Sequence
from pathlib import Path

from src.txt2speech.config import Settings, parse_chapter_range
from src.txt2speech.errors import InputError
from src.txt2speech.models import Chapter
from src.txt2speech.pdf_input import read_pdf_chapters
from src.txt2speech.structure import split_chapters
from src.txt2speech.text_io import read_text

_PDF_SUFFIX = ".pdf"


def load_chapters(input_path: Path, settings: Settings) -> list[Chapter]:
    if input_path.suffix.lower() == _PDF_SUFFIX:
        return read_pdf_chapters(input_path, settings)
    return split_chapters(read_text(input_path))


def _in_range(index: int, first: int | None, last: int | None) -> bool:
    if first is not None and index < first:
        return False
    return not (last is not None and index > last)


def select_chapters(
    chapters: Sequence[Chapter],
    spec: str | None,
) -> list[tuple[int, Chapter]]:
    indexed = list(enumerate(chapters, start=1))
    if spec is None:
        return indexed
    first, last = parse_chapter_range(spec)
    selected = [(idx, ch) for idx, ch in indexed if _in_range(idx, first, last)]
    if not selected:
        msg = f"指定した範囲に章がありません ({len(chapters)}章中 {spec})"
        raise InputError(msg)
    return selected
