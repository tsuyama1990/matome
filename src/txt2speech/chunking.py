import re

from src.txt2speech.config import DEFAULT_MAX_CHUNK_CHARS, DEFAULT_MIN_CHUNK_CHARS
from src.txt2speech.models import Boundary, Chunk

_PARAGRAPH_SPLIT_RE = re.compile(r"\n\s*\n+")
_SENTENCE_END_RE = re.compile(r"[。！？!?]+[。！？!?」』）)]*")
_COMMA_RE = re.compile(r"[、，,]+")

_KANJI_RE = re.compile(r"[一-龥々〆ヶ]")
_HIRAGANA_RE = re.compile(r"[ぁ-ゟ]")
_KATAKANA_RE = re.compile(r"[゠-ヿ]")
_ALNUM_RE = re.compile(r"[0-9A-Za-z０-９Ａ-Ｚａ-ｚ]")


def _char_class(ch: str) -> str:
    if _KANJI_RE.match(ch):
        return "kanji"
    if _HIRAGANA_RE.match(ch):
        return "hiragana"
    if _KATAKANA_RE.match(ch):
        return "katakana"
    if _ALNUM_RE.match(ch):
        return "alnum"
    return "other"


def _find_force_split_pos(text: str, max_chars: int) -> int:
    # Walk backwards from max_chars to avoid splitting inside a same-class run.
    for pos in range(max_chars, 0, -1):
        if _char_class(text[pos - 1]) != _char_class(text[pos]):
            return pos
    return max_chars


def _split_into_sentences(paragraph: str) -> list[tuple[str, Boundary]]:
    sentences: list[tuple[str, Boundary]] = []
    start = 0
    for match in _SENTENCE_END_RE.finditer(paragraph):
        end = match.end()
        sentences.append((paragraph[start:end], "sentence"))
        start = end
    if start < len(paragraph):
        sentences.append((paragraph[start:], "other"))
    return sentences


def _split_by_commas(
    sentence: str,
    final_boundary: Boundary,
) -> list[tuple[str, Boundary]]:
    clauses: list[tuple[str, Boundary]] = []
    start = 0
    for match in _COMMA_RE.finditer(sentence):
        end = match.end()
        boundary: Boundary = "comma" if end < len(sentence) else final_boundary
        clauses.append((sentence[start:end], boundary))
        start = end
    if start < len(sentence):
        clauses.append((sentence[start:], final_boundary))
    return clauses


def _force_split_clause(
    clause_text: str,
    max_chars: int,
) -> tuple[list[Chunk], str]:
    forced: list[Chunk] = []
    remaining = clause_text
    while len(remaining) > max_chars:
        cut = _find_force_split_pos(remaining, max_chars)
        forced.append(Chunk(text=remaining[:cut], boundary="other"))
        remaining = remaining[cut:]
    return forced, remaining


def _split_long_sentence(
    sentence: str,
    final_boundary: Boundary,
    max_chars: int,
) -> list[Chunk]:
    clauses = _split_by_commas(sentence, final_boundary)
    chunks: list[Chunk] = []
    buf_text = ""
    buf_boundary: Boundary = "comma"

    for clause_text, clause_boundary in clauses:
        if buf_text and len(buf_text) + len(clause_text) <= max_chars:
            buf_text += clause_text
            buf_boundary = clause_boundary
            continue

        if buf_text:
            chunks.append(Chunk(text=buf_text, boundary=buf_boundary))
            buf_text = ""

        forced_chunks, remainder = _force_split_clause(clause_text, max_chars)
        chunks.extend(forced_chunks)
        buf_text = remainder
        buf_boundary = clause_boundary

    if buf_text:
        chunks.append(Chunk(text=buf_text, boundary=buf_boundary))

    return chunks


def _split_paragraph(paragraph: str, max_chars: int) -> list[Chunk]:
    para_chunks: list[Chunk] = []
    for sentence, boundary in _split_into_sentences(paragraph):
        if len(sentence) <= max_chars:
            para_chunks.append(Chunk(text=sentence, boundary=boundary))
        else:
            para_chunks.extend(_split_long_sentence(sentence, boundary, max_chars))

    last = para_chunks[-1]
    para_chunks[-1] = Chunk(text=last.text, boundary="paragraph")
    return para_chunks


def split_chunks(
    body: str,
    max_chars: int = DEFAULT_MAX_CHUNK_CHARS,
) -> list[Chunk]:
    chunks: list[Chunk] = []
    for raw_para in _PARAGRAPH_SPLIT_RE.split(body):
        paragraph = raw_para.strip()
        if not paragraph:
            continue
        chunks.extend(_split_paragraph(paragraph, max_chars))
    return chunks


def halve(
    text: str,
    min_chars: int = DEFAULT_MIN_CHUNK_CHARS,
) -> tuple[str, str] | None:
    effective_min = max(1, min_chars)
    if len(text) < 2 * effective_min:
        return None

    mid = len(text) // 2
    change_positions = [
        pos for pos in range(1, len(text)) if _char_class(text[pos - 1]) != _char_class(text[pos])
    ]
    if not change_positions:
        return (text[:mid], text[mid:])

    best = min(change_positions, key=lambda pos: abs(pos - mid))
    if best < effective_min or len(text) - best < effective_min:
        best = mid
    return (text[:best], text[best:])
