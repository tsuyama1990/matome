import re
import statistics
import unicodedata
from collections import Counter
from collections.abc import Iterator, Mapping, Sequence, Set
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

from pdfminer.high_level import extract_pages
from pdfminer.layout import LTChar, LTPage, LTTextContainer, LTTextLine
from pdfminer.pdfdocument import PDFDocument, PDFNoOutlines
from pdfminer.pdfpage import PDFPage
from pdfminer.pdfparser import PDFParser
from pdfminer.pdftypes import PDFException, PDFObjRef, resolve1
from pdfminer.psparser import PSException
from pdfminer.utils import decode_text

from src.txt2speech.config import Settings
from src.txt2speech.errors import InputError
from src.txt2speech.models import Chapter

_GARBAGE_CATEGORIES: frozenset[str] = frozenset({"Cc", "Co", "Cn"})
_REPLACEMENT_CHAR = "\ufffd"
_TRAILING_OPEN_PARENS = " \t\r\n\u3000(（"
_WHITESPACE_RUN_RE = re.compile(r"\s+")
_MULTI_SPACE_RE = re.compile(r"[ 　]{2,}")
_DIGITS_ONLY_RE = re.compile(r"^[0-9０-９]+$")
_NOTE_MARKER_RE = re.compile(
    r"注[0-9０-９]+(?:[・，、,][0-9０-９]+)*(?!を参照|参照|を見|のとおり|の通り)"
)
_SENTENCE_END_CHARS: frozenset[str] = frozenset("。！？!?」』）)")
_IGNORED_META_TITLES: frozenset[str] = frozenset({"untitled", "(anonymous)"})

_CHAR_SIZE_ROUND_DIGITS = 1
_DEFAULT_BODY_SIZE_PT = 10.0
_DEFAULT_LEADING_PT = 18.0
_DEFAULT_SETTINGS = Settings()


@dataclass(frozen=True)
class OutlineEntry:
    level: int
    title: str
    page: int


@dataclass(frozen=True)
class LineRecord:
    page: int
    text: str
    x0: float
    y0: float
    size: float


@dataclass(frozen=True)
class ChapterSpan:
    title: str
    start_page: int
    end_page: int


def _is_ascii_alnum(ch: str) -> bool:
    return ch.isascii() and ch.isalnum()


def _truncate_at_garbage(raw: str) -> str:
    for idx, ch in enumerate(raw):
        if ch == _REPLACEMENT_CHAR or unicodedata.category(ch) in _GARBAGE_CATEGORIES:
            return raw[:idx]
    return raw


def clean_title(raw: str) -> str:
    truncated = _truncate_at_garbage(raw)
    if not truncated:
        return ""

    def _replace_space(match: re.Match[str]) -> str:
        start, end = match.span()
        if (
            start > 0
            and end < len(truncated)
            and _is_ascii_alnum(truncated[start - 1])
            and _is_ascii_alnum(truncated[end])
        ):
            return " "
        return ""

    compact = _WHITESPACE_RUN_RE.sub(_replace_space, truncated)
    return compact.strip().rstrip(_TRAILING_OPEN_PARENS)


def _normalize_for_title_match(text: str) -> str:
    return "".join(ch for ch in unicodedata.normalize("NFKC", text) if not ch.isspace())


def _build_normalized_page_index(page_raw: str) -> tuple[str, list[int]]:
    norm_chars: list[str] = []
    end_offsets: list[int] = []
    for idx, ch in enumerate(page_raw):
        if ch.isspace():
            continue
        for norm_ch in _normalize_for_title_match(ch):
            norm_chars.append(norm_ch)
            end_offsets.append(idx + 1)
    return "".join(norm_chars), end_offsets


def reconcile_title(
    outline_title: str,
    first_lines: Sequence[str],
    settings: Settings = _DEFAULT_SETTINGS,
) -> str:
    if not outline_title:
        return ""
    if not first_lines:
        return outline_title

    outline_norm = _normalize_for_title_match(outline_title)
    page_raw = " ".join(first_lines)
    page_norm, end_offsets = _build_normalized_page_index(page_raw)

    match_len = 0
    for out_ch, page_ch in zip(outline_norm, page_norm, strict=False):
        if out_ch != page_ch:
            break
        match_len += 1

    if match_len < settings.pdf_title_min_match:
        return outline_title

    matched_raw = page_raw[: end_offsets[match_len - 1]]
    return clean_title(matched_raw)


def select_chapters(
    entries: Sequence[OutlineEntry],
    max_level: int,
    last_page: int,
) -> list[ChapterSpan]:
    by_page: dict[int, OutlineEntry] = {}
    for entry in entries:
        if 1 <= entry.level <= max_level and 1 <= entry.page <= last_page:
            by_page[entry.page] = entry

    ordered = [by_page[page] for page in sorted(by_page)]
    spans: list[ChapterSpan] = []
    for idx, entry in enumerate(ordered):
        end_page = ordered[idx + 1].page - 1 if idx + 1 < len(ordered) else last_page
        if entry.page <= end_page:
            spans.append(
                ChapterSpan(
                    title=entry.title,
                    start_page=entry.page,
                    end_page=end_page,
                )
            )
    return spans


def median_body_size(lines: Sequence[LineRecord]) -> float:
    if not lines:
        return _DEFAULT_BODY_SIZE_PT
    return float(statistics.median(line.size for line in lines))


def find_repeated_texts(
    lines: Sequence[LineRecord],
    settings: Settings = _DEFAULT_SETTINGS,
    total_pages: int | None = None,
) -> set[str]:
    page_count = total_pages if total_pages is not None else len({line.page for line in lines})
    if page_count < settings.pdf_repeat_min_pages:
        return set()

    pages_by_text: dict[str, set[int]] = {}
    for line in lines:
        stripped = line.text.strip()
        if stripped:
            pages_by_text.setdefault(stripped, set()).add(line.page)

    return {
        text
        for text, pages in pages_by_text.items()
        if len(pages) / page_count >= settings.pdf_repeat_page_ratio
    }


def drop_noise(
    lines: Sequence[LineRecord],
    body_size: float | Settings | None = None,
    repeated: Set[str] | None = None,
    settings: Settings | None = None,
) -> list[LineRecord]:
    if isinstance(body_size, Settings):
        effective_settings = body_size
        effective_body_size = median_body_size(lines)
    else:
        effective_settings = settings if settings is not None else _DEFAULT_SETTINGS
        effective_body_size = body_size if body_size is not None else median_body_size(lines)

    effective_repeated = (
        repeated if repeated is not None else find_repeated_texts(lines, effective_settings)
    )
    min_size = effective_body_size * effective_settings.pdf_footnote_size_ratio

    kept: list[LineRecord] = []
    for line in lines:
        stripped = line.text.strip()
        if not stripped:
            continue
        if line.size < min_size:
            continue
        if _DIGITS_ONLY_RE.match(stripped) is not None:
            continue
        if stripped in effective_repeated:
            continue
        kept.append(line)
    return kept


def _join_line_texts(prev_text: str, next_text: str) -> str:
    if prev_text and next_text and _is_ascii_alnum(prev_text[-1]) and _is_ascii_alnum(next_text[0]):
        return f"{prev_text} {next_text}"
    return f"{prev_text}{next_text}"


def _page_leading(sorted_page_lines: Sequence[LineRecord]) -> float:
    gaps = [
        sorted_page_lines[idx - 1].y0 - sorted_page_lines[idx].y0
        for idx in range(1, len(sorted_page_lines))
    ]
    positive_gaps = [gap for gap in gaps if gap > 0.0]
    return float(statistics.median(positive_gaps)) if positive_gaps else _DEFAULT_LEADING_PT


def _page_margin(
    sorted_page_lines: Sequence[LineRecord],
    global_margin: float,
    tolerance: float,
) -> float:
    min_x = min(line.x0 for line in sorted_page_lines)
    max_x = max(line.x0 for line in sorted_page_lines)
    if max_x - min_x > tolerance:
        return min_x
    return global_margin


def _should_join_same_page(
    prev_line: LineRecord,
    curr_line: LineRecord,
    margin: float,
    max_gap: float,
    tolerance: float,
) -> bool:
    if curr_line.x0 > margin + tolerance:
        return False
    gap = prev_line.y0 - curr_line.y0
    return gap <= max_gap


def _should_join_across_pages(
    prev_paragraph: str,
    first_line: LineRecord,
    margin: float,
    tolerance: float,
) -> bool:
    if not prev_paragraph or prev_paragraph[-1] in _SENTENCE_END_CHARS:
        return False
    return first_line.x0 <= margin + tolerance


def assemble_paragraphs(
    lines: Sequence[LineRecord],
    settings: Settings = _DEFAULT_SETTINGS,
) -> str:
    non_empty = [line for line in lines if line.text.strip()]
    if not non_empty:
        return ""

    global_margin = min(line.x0 for line in non_empty)
    by_page: dict[int, list[LineRecord]] = {}
    for line in non_empty:
        by_page.setdefault(line.page, []).append(line)

    paragraphs: list[str] = []
    tolerance = settings.pdf_indent_tolerance_pt
    for page_num in sorted(by_page):
        page_lines = sorted(by_page[page_num], key=lambda item: (-item.y0, item.x0))
        margin = _page_margin(page_lines, global_margin, tolerance)
        max_gap = _page_leading(page_lines) * settings.pdf_paragraph_gap_ratio

        first_text = page_lines[0].text.strip()
        if paragraphs and _should_join_across_pages(
            paragraphs[-1], page_lines[0], margin, tolerance
        ):
            paragraphs[-1] = _join_line_texts(paragraphs[-1], first_text)
        else:
            paragraphs.append(first_text)

        for idx in range(1, len(page_lines)):
            curr_text = page_lines[idx].text.strip()
            if _should_join_same_page(
                page_lines[idx - 1], page_lines[idx], margin, max_gap, tolerance
            ):
                paragraphs[-1] = _join_line_texts(paragraphs[-1], curr_text)
            else:
                paragraphs.append(curr_text)

    return "\n\n".join(paragraphs)


def strip_note_markers(text: str) -> str:
    return _NOTE_MARKER_RE.sub("", text)


def collapse_spaces(text: str) -> str:
    return _MULTI_SPACE_RE.sub(" ", text)


def _resolve_dest_target(doc: PDFDocument, dest: Any, action: Any) -> Any:
    target = dest
    if target is None and action is not None:
        resolved_action = resolve1(action)
        if isinstance(resolved_action, dict):
            target = resolved_action.get("D")
    target = resolve1(target)
    if isinstance(target, (bytes, str)):
        try:
            target = doc.get_dest(target)
        except (PSException, PDFException, KeyError, TypeError):
            return None
        target = resolve1(target)
    if isinstance(target, dict):
        target = resolve1(target.get("D"))
    return target


def _resolve_dest_page(
    doc: PDFDocument,
    dest: Any,
    action: Any,
    page_id_to_num: Mapping[int, int],
) -> int | None:
    target = _resolve_dest_target(doc, dest, action)
    if isinstance(target, (list, tuple)) and target:
        page_ref = target[0]
        if isinstance(page_ref, PDFObjRef):
            return page_id_to_num.get(page_ref.objid)
    return None


def _extract_doc_outlines(
    doc: PDFDocument,
    page_id_to_num: Mapping[int, int],
) -> list[OutlineEntry]:
    try:
        raw_outlines = doc.get_outlines()
        entries: list[OutlineEntry] = []
        for level, title, dest, action, _se in raw_outlines:
            page_num = _resolve_dest_page(doc, dest, action, page_id_to_num)
            if page_num is not None and isinstance(title, str):
                entries.append(OutlineEntry(level=int(level), title=title, page=page_num))
    except (PDFNoOutlines, KeyError):
        return []
    else:
        return entries


def _extract_doc_title(doc: PDFDocument) -> str:
    for info in doc.info:
        if not isinstance(info, dict) or "Title" not in info:
            continue
        raw_title = resolve1(info["Title"])
        if isinstance(raw_title, bytes):
            decoded = decode_text(raw_title)
        elif isinstance(raw_title, str):
            decoded = raw_title
        else:
            continue
        cleaned = clean_title(decoded)
        if cleaned and cleaned.lower() not in _IGNORED_META_TITLES:
            return cleaned
    return ""


def _read_pdf_structure(path: Path) -> tuple[int, str, list[OutlineEntry]]:
    if not path.is_file():
        msg = f"入力ファイルが見つかりません: {path.name}"
        raise InputError(msg)
    try:
        with path.open("rb") as fp:
            parser = PDFParser(fp)
            doc = PDFDocument(parser)
            is_extractable = bool(doc.is_extractable)
            page_id_to_num: dict[int, int] = (
                {
                    cast("int", page.pageid): idx + 1
                    for idx, page in enumerate(PDFPage.create_pages(doc))
                }
                if is_extractable
                else {}
            )
            outlines = _extract_doc_outlines(doc, page_id_to_num) if is_extractable else []
            meta_title = _extract_doc_title(doc) if is_extractable else ""
    except (PSException, PDFException, OSError, ValueError, TypeError, KeyError, EOFError) as exc:
        msg = f"PDF の読み込みに失敗しました: {path.name}"
        raise InputError(msg) from exc

    if not is_extractable:
        msg = f"暗号化された PDF は読み込めません: {path.name}"
        raise InputError(msg)
    return len(page_id_to_num), meta_title, outlines


def read_outline(path: Path) -> list[OutlineEntry]:
    _, _, outlines = _read_pdf_structure(path)
    return outlines


def _line_char_size(text_line: LTTextLine) -> float:
    non_space_sizes = [
        round(float(item.size), _CHAR_SIZE_ROUND_DIGITS)
        for item in text_line
        if isinstance(item, LTChar) and not item.get_text().isspace()
    ]
    if non_space_sizes:
        return Counter(non_space_sizes).most_common(1)[0][0]
    all_sizes = [
        round(float(item.size), _CHAR_SIZE_ROUND_DIGITS)
        for item in text_line
        if isinstance(item, LTChar)
    ]
    if all_sizes:
        return Counter(all_sizes).most_common(1)[0][0]
    return round(float(text_line.height), _CHAR_SIZE_ROUND_DIGITS)


def _iter_page_lines(page_num: int, page_layout: LTPage) -> Iterator[LineRecord]:
    for element in page_layout:
        if not isinstance(element, LTTextContainer):
            continue
        for text_line in element:
            if not isinstance(text_line, LTTextLine):
                continue
            text = text_line.get_text().strip()
            if not text:
                continue
            yield LineRecord(
                page=page_num,
                text=text,
                x0=float(text_line.x0),
                y0=float(text_line.y0),
                size=_line_char_size(text_line),
            )


def _extract_single_page(path: Path, page_num: int) -> Iterator[LineRecord]:
    for page_layout in extract_pages(path, page_numbers=[page_num - 1]):
        yield from _iter_page_lines(page_num, page_layout)


def extract_lines(
    path: Path,
    pages: Sequence[int] | None = None,
) -> Iterator[LineRecord]:
    if not path.is_file():
        msg = f"入力ファイルが見つかりません: {path.name}"
        raise InputError(msg)

    try:
        if pages is None:
            for idx, page_layout in enumerate(extract_pages(path), start=1):
                yield from _iter_page_lines(idx, page_layout)
        else:
            for page_num in pages:
                yield from _extract_single_page(path, page_num)
    except (PSException, PDFException, OSError, ValueError, TypeError, KeyError, EOFError) as exc:
        msg = f"PDF の読み込みに失敗しました: {path.name}"
        raise InputError(msg) from exc


def _build_chapter_spans(
    outlines: Sequence[OutlineEntry],
    meta_title: str,
    default_stem: str,
    total_pages: int,
    outline_level: int,
) -> list[ChapterSpan]:
    selected = select_chapters(outlines, outline_level, total_pages)
    if selected:
        return [
            ChapterSpan(
                title=clean_title(span.title),
                start_page=span.start_page,
                end_page=span.end_page,
            )
            for span in selected
        ]
    fallback_title = meta_title or default_stem
    return [ChapterSpan(title=fallback_title, start_page=1, end_page=total_pages)]


def _start_page_first_lines(
    filtered_lines: Sequence[LineRecord],
    start_page: int,
    max_lines: int,
) -> list[str]:
    start_lines = [line for line in filtered_lines if line.page == start_page]
    start_lines.sort(key=lambda item: (-item.y0, item.x0))
    return [line.text for line in start_lines[:max_lines]]


def read_pdf_chapters(
    path: Path,
    settings: Settings = _DEFAULT_SETTINGS,
) -> list[Chapter]:
    total_pages, meta_title, outlines = _read_pdf_structure(path)
    if total_pages == 0:
        return []

    spans = _build_chapter_spans(
        outlines=outlines,
        meta_title=meta_title,
        default_stem=path.stem,
        total_pages=total_pages,
        outline_level=settings.pdf_outline_level,
    )
    used_pages = [
        page_num for span in spans for page_num in range(span.start_page, span.end_page + 1)
    ]
    all_lines = list(extract_lines(path, used_pages))
    if not all_lines:
        return []

    body_size = median_body_size(all_lines)
    repeated = find_repeated_texts(all_lines, settings, total_pages=len(used_pages))

    chapters: list[Chapter] = []
    for span in spans:
        span_lines = [line for line in all_lines if span.start_page <= line.page <= span.end_page]
        filtered = drop_noise(span_lines, body_size, repeated, settings)
        first_lines = _start_page_first_lines(filtered, span.start_page, settings.pdf_title_lines)
        title = reconcile_title(span.title, first_lines, settings)
        assembled = assemble_paragraphs(filtered, settings)
        body = collapse_spaces(strip_note_markers(assembled)).strip()
        if body:
            chapters.append(Chapter(title=title, body=body))
    return chapters
