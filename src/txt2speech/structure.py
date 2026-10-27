import re

from src.txt2speech.config import MAX_CHAPTER_TITLE_CHARS, MIN_CHAPTER_INDEX_WIDTH
from src.txt2speech.models import Chapter

_MD_HEADING_LINE_RE = re.compile(r"^#{1,2}\s+(\S.*)$")
_NUMBERED_HEADING_LINE_RE = re.compile(r"^(\d+(?:\.\d+)+)\s+(\S.*)$")
_CHAPTER_HEADING_LINE_RE = re.compile(r"^(第[0-9０-９一二三四五六七八九十百]+[章節])\s*(.*)$")
_FORBIDDEN_FILENAME_CHARS_RE = re.compile(r'[\x00-\x1f\x7f/\\:*?"<>|]')
_STRIP_FILENAME_CHARS = " \t\r\n.\u3000"


def _extract_heading_title(line: str) -> str | None:
    md_match = _MD_HEADING_LINE_RE.match(line)
    if md_match is not None:
        return md_match.group(1).strip()

    num_match = _NUMBERED_HEADING_LINE_RE.match(line)
    if num_match is not None:
        return f"{num_match.group(1)} {num_match.group(2).strip()}"

    chap_match = _CHAPTER_HEADING_LINE_RE.match(line)
    if chap_match is not None:
        prefix = chap_match.group(1)
        rest = chap_match.group(2).strip()
        return f"{prefix} {rest}" if rest else prefix

    return None


def _append_chapter_if_nonempty(
    chapters: list[Chapter],
    title: str,
    lines: list[str],
) -> None:
    body = "\n".join(lines).strip("\n")
    if body.strip():
        chapters.append(Chapter(title=title, body=body))


def split_chapters(text: str) -> list[Chapter]:
    if not text.strip():
        return []

    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = normalized.split("\n")

    chapters: list[Chapter] = []
    current_title = ""
    current_lines: list[str] = []
    found_heading = False

    for line in lines:
        heading_title = _extract_heading_title(line)
        if heading_title is not None:
            _append_chapter_if_nonempty(chapters, current_title, current_lines)
            current_title = heading_title
            current_lines = []
            found_heading = True
        else:
            current_lines.append(line)

    if not found_heading:
        return [Chapter(title="", body=text)]

    _append_chapter_if_nonempty(chapters, current_title, current_lines)
    return chapters


def chapter_filename(
    index: int,
    title: str,
    width: int = MIN_CHAPTER_INDEX_WIDTH,
) -> str:
    effective_width = max(MIN_CHAPTER_INDEX_WIDTH, width)
    prefix = f"{index:0{effective_width}d}"
    sanitized = _FORBIDDEN_FILENAME_CHARS_RE.sub("_", title)
    sanitized = sanitized.strip(_STRIP_FILENAME_CHARS)
    sanitized = sanitized[:MAX_CHAPTER_TITLE_CHARS].strip(_STRIP_FILENAME_CHARS)
    if not sanitized:
        return f"{prefix}.mp3"
    return f"{prefix}_{sanitized}.mp3"
