import csv
import io
import re
from dataclasses import dataclass

from src.txt2speech.errors import InputError

_EXPECTED_COLUMNS = 3
_HEADER_LINE_NUMBER = 1
_MIN_ACCENT_TYPE = 0
_KATAKANA_RE = re.compile(r"^[ァ-ヶー]+$")


@dataclass(frozen=True)
class DictEntry:
    surface: str
    pronunciation: str
    accent_type: int


def _parse_row(row: list[str], source: str, line_no: int) -> DictEntry:
    if len(row) != _EXPECTED_COLUMNS:
        msg = f"{source}:{line_no}: 3 列 (表記, カタカナ読み, アクセント核位置) が必要です"
        raise InputError(msg)

    surface = row[0].strip()
    pronunciation = row[1].strip()
    accent_raw = row[2].strip()

    if not surface:
        msg = f"{source}:{line_no}: 表記が空です"
        raise InputError(msg)

    if not _KATAKANA_RE.match(pronunciation):
        msg = f"{source}:{line_no}: 読みはカタカナで指定してください: {pronunciation}"
        raise InputError(msg)

    try:
        accent_type = int(accent_raw)
    except ValueError as exc:
        msg = f"{source}:{line_no}: アクセント核位置は整数で指定してください: {accent_raw}"
        raise InputError(msg) from exc

    if accent_type < _MIN_ACCENT_TYPE:
        msg = f"{source}:{line_no}: アクセント核位置は 0 以上で指定してください: {accent_type}"
        raise InputError(msg)

    return DictEntry(
        surface=surface,
        pronunciation=pronunciation,
        accent_type=accent_type,
    )


def parse_dictionary(text: str, source: str) -> list[DictEntry]:
    if not text.strip():
        return []

    reader = csv.reader(io.StringIO(text))
    entries: list[DictEntry] = []
    for line_no, row in enumerate(reader, start=1):
        if line_no == _HEADER_LINE_NUMBER:
            continue
        if not row or all(not cell.strip() for cell in row):
            continue
        entries.append(_parse_row(row, source, line_no))
    return entries
