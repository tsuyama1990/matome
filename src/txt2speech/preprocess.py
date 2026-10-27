import re

from src.txt2speech.reading_table import READINGS

_AOZORA_EXPLICIT_RUBY_RE = re.compile(r"\|[^《\n|]+《([^》]+)》")
_AOZORA_KANJI_RUBY_RE = re.compile(r"([一-龥々〆ヶ]+)《([^》]+)》")
_MARKDOWN_RUBY_RE = re.compile(r"\[([^\]]+)\]\(([ぁ-ゟ゠-ヿー]+)\)")
_HTML_RUBY_RE = re.compile(r"<ruby>(.*?)</ruby>", re.DOTALL)
_HTML_RP_RE = re.compile(r"<rp>.*?</rp>", re.DOTALL)
_HTML_RT_RE = re.compile(r"<rt>(.*?)</rt>", re.DOTALL)

_SEPARATOR_LINE_RE = re.compile(r"^[-=_*─—–\s]{3,}$")
_SEPARATOR_CHAR_RE = re.compile(r"[-=_*─—–]")
_PAGE_LABEL_LINE_RE = re.compile(r"^[-—–─\s]*\d+\s*ページ[-—–─\s]*$")
_PAGE_NUMBER_LINE_RE = re.compile(r"^\s*-?\s*\d+\s*-?\s*$")

_FIGURE_REF_RE = re.compile(r"[図表](?:\d+[-－]\d+|\d+)|\[写真\]|※[^\n]*")
_MULTI_SPACE_RE = re.compile(r"[ \t]{2,}")

_COMMA_NUMBER_RE = re.compile(r"(?<!\d)\d{1,3}(?:,\d{3})+(?!\d)")

_BULLET_PREFIX_RE = re.compile(r"^\s*(?:(?:[-*+]|\d+[.)])\s+|[・①-⑳]\s*)")
_SENTENCE_END_CHARS = "。！？!?"
_JAPANESE_PERIOD = "。"

_MD_HEADING_RE = re.compile(r"^#+[ \t]+", re.MULTILINE)
_MD_QUOTE_RE = re.compile(r"^>[ \t]+", re.MULTILINE)
_MD_INLINE_RE = re.compile(r"\*\*|__|`")

_MULTI_NEWLINE_RE = re.compile(r"\n{3,}")

_SORTED_READING_KEYS: tuple[str, ...] = tuple(sorted(READINGS.keys(), key=len, reverse=True))


def _replace_html_ruby(match: re.Match[str]) -> str:
    inner = _HTML_RP_RE.sub("", match.group(1))
    readings = _HTML_RT_RE.findall(inner)
    return "".join(readings)


def _replace_ruby(text: str) -> str:
    text = _AOZORA_EXPLICIT_RUBY_RE.sub(r"\1", text)
    text = _AOZORA_KANJI_RUBY_RE.sub(r"\2", text)
    text = _MARKDOWN_RUBY_RE.sub(r"\2", text)
    return _HTML_RUBY_RE.sub(_replace_html_ruby, text)


def _is_removable_line(line: str) -> bool:
    if _PAGE_LABEL_LINE_RE.match(line) or _PAGE_NUMBER_LINE_RE.match(line):
        return True
    return bool(_SEPARATOR_LINE_RE.match(line) and _SEPARATOR_CHAR_RE.search(line))


def _remove_noise_lines(text: str) -> str:
    kept = [line for line in text.split("\n") if not _is_removable_line(line)]
    return "\n".join(kept)


def _remove_figure_refs(text: str) -> str:
    cleaned = _FIGURE_REF_RE.sub("", text)
    return _MULTI_SPACE_RE.sub(" ", cleaned)


def _apply_reading_table(text: str) -> str:
    for key in _SORTED_READING_KEYS:
        text = text.replace(key, READINGS[key])
    return text


def _normalize_bullet_line(line: str) -> str:
    match = _BULLET_PREFIX_RE.match(line)
    if match is None:
        return line
    body = line[match.end() :].rstrip()
    if not body:
        return ""
    if body[-1] not in _SENTENCE_END_CHARS:
        return f"{body}{_JAPANESE_PERIOD}"
    return body


def _normalize_bullets(text: str) -> str:
    return "\n".join(_normalize_bullet_line(line) for line in text.split("\n"))


def _strip_markdown(text: str) -> str:
    text = _MD_HEADING_RE.sub("", text)
    text = _MD_QUOTE_RE.sub("", text)
    return _MD_INLINE_RE.sub("", text)


def normalize(text: str) -> str:
    # Normalize line endings to LF before line-oriented regex rules run.
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = _replace_ruby(text)
    text = _remove_noise_lines(text)
    text = _remove_figure_refs(text)
    text = _apply_reading_table(text)
    text = _COMMA_NUMBER_RE.sub(lambda m: m.group(0).replace(",", ""), text)
    text = _normalize_bullets(text)
    text = _strip_markdown(text)
    text = _MULTI_NEWLINE_RE.sub("\n\n", text)
    return text.strip()
