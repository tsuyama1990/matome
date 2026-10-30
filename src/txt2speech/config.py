from collections.abc import Mapping
from dataclasses import dataclass, fields
from pathlib import Path
from types import MappingProxyType
from typing import Any
from urllib.parse import urlparse

import yaml

from src.txt2speech.errors import InputError

DEFAULT_ENGINE_URL = "http://127.0.0.1:50021"
DEFAULT_SPEAKER = 1
DEFAULT_SPEED_SCALE = 1.1
DEFAULT_PITCH_SCALE = 0.0
DEFAULT_INTONATION_SCALE = 1.0
DEFAULT_VOLUME_SCALE = 1.0
DEFAULT_MAX_CHUNK_CHARS = 80
DEFAULT_MIN_CHUNK_CHARS = 4
DEFAULT_RETRIES = 3
DEFAULT_RETRY_WAIT_SECONDS = 0.5
DEFAULT_REQUEST_TIMEOUT_SECONDS = 60.0
DEFAULT_PAUSE_MS: Mapping[str, int] = MappingProxyType(
    {
        "paragraph": 900,
        "sentence": 450,
        "comma": 200,
        "other": 100,
    }
)
DEFAULT_FFMPEG_PATH = "ffmpeg"
DEFAULT_LOUDNESS_LUFS = -16.0
DEFAULT_TRUE_PEAK_DBFS = -1.0
DEFAULT_LOUDNESS_RANGE = 11.0
DEFAULT_SAMPLE_RATE_HZ = 44100
DEFAULT_BITRATE = "128k"
DEFAULT_VOICE_NAME = "VOICEVOX"
DEFAULT_GENRE = "Audiobook"
DEFAULT_WORK_DIR_NAME = ".txt2speech_work"
DEFAULT_PROGRESS_FILE_NAME = ".txt2speech_progress.json"
DEFAULT_CHAPTERS: str | None = None
DEFAULT_PDF_TITLE_MIN_MATCH = 3
DEFAULT_PDF_TITLE_LINES = 6
DEFAULT_PDF_OUTLINE_LEVEL = 1
DEFAULT_PDF_FOOTNOTE_SIZE_RATIO = 0.85
DEFAULT_PDF_REPEAT_PAGE_RATIO = 0.4
DEFAULT_PDF_REPEAT_MIN_PAGES = 3
DEFAULT_PDF_INDENT_TOLERANCE_PT = 5.0
DEFAULT_PDF_PARAGRAPH_GAP_RATIO = 1.4

MIN_SPEED_SCALE = 0.5
MAX_SPEED_SCALE = 2.0
MIN_RETRIES = 0
MIN_CHAPTER_NUMBER = 1
MIN_PDF_TITLE_MIN_MATCH = 1
MIN_PDF_TITLE_LINES = 1
MIN_PDF_OUTLINE_LEVEL = 1
MIN_PDF_REPEAT_MIN_PAGES = 2
MAX_PDF_RATIO = 1.0
PAUSE_KEYS: frozenset[str] = frozenset(DEFAULT_PAUSE_MS.keys())
LOOPBACK_HOSTS: frozenset[str] = frozenset({"127.0.0.1", "localhost", "::1"})
ALLOWED_URL_SCHEMES: frozenset[str] = frozenset({"http", "https"})

MAX_CHAPTER_TITLE_CHARS = 80
MIN_CHAPTER_INDEX_WIDTH = 2


@dataclass(frozen=True)
class Settings:
    engine_url: str = DEFAULT_ENGINE_URL
    speaker: int = DEFAULT_SPEAKER
    speed_scale: float = DEFAULT_SPEED_SCALE
    pitch_scale: float = DEFAULT_PITCH_SCALE
    intonation_scale: float = DEFAULT_INTONATION_SCALE
    volume_scale: float = DEFAULT_VOLUME_SCALE
    max_chunk_chars: int = DEFAULT_MAX_CHUNK_CHARS
    min_chunk_chars: int = DEFAULT_MIN_CHUNK_CHARS
    retries: int = DEFAULT_RETRIES
    retry_wait_seconds: float = DEFAULT_RETRY_WAIT_SECONDS
    request_timeout_seconds: float = DEFAULT_REQUEST_TIMEOUT_SECONDS
    pause_ms: Mapping[str, int] = DEFAULT_PAUSE_MS
    ffmpeg_path: str = DEFAULT_FFMPEG_PATH
    loudness_lufs: float = DEFAULT_LOUDNESS_LUFS
    true_peak_dbfs: float = DEFAULT_TRUE_PEAK_DBFS
    loudness_range: float = DEFAULT_LOUDNESS_RANGE
    sample_rate_hz: int = DEFAULT_SAMPLE_RATE_HZ
    bitrate: str = DEFAULT_BITRATE
    voice_name: str = DEFAULT_VOICE_NAME
    genre: str = DEFAULT_GENRE
    album: str | None = None
    cover: Path | None = None
    dictionaries: tuple[Path, ...] = ()
    work_dir_name: str = DEFAULT_WORK_DIR_NAME
    progress_file_name: str = DEFAULT_PROGRESS_FILE_NAME
    chapters: str | None = DEFAULT_CHAPTERS
    pdf_title_min_match: int = DEFAULT_PDF_TITLE_MIN_MATCH
    pdf_title_lines: int = DEFAULT_PDF_TITLE_LINES
    pdf_outline_level: int = DEFAULT_PDF_OUTLINE_LEVEL
    pdf_footnote_size_ratio: float = DEFAULT_PDF_FOOTNOTE_SIZE_RATIO
    pdf_repeat_page_ratio: float = DEFAULT_PDF_REPEAT_PAGE_RATIO
    pdf_repeat_min_pages: int = DEFAULT_PDF_REPEAT_MIN_PAGES
    pdf_indent_tolerance_pt: float = DEFAULT_PDF_INDENT_TOLERANCE_PT
    pdf_paragraph_gap_ratio: float = DEFAULT_PDF_PARAGRAPH_GAP_RATIO


def read_yaml(path: Path) -> dict[str, Any]:
    if not path.is_file():
        msg = f"設定ファイルが見つかりません: {path}"
        raise InputError(msg)
    try:
        loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        msg = f"設定ファイルの読み込みに失敗しました: {path}"
        raise InputError(msg) from exc
    if loaded is None:
        return {}
    if not isinstance(loaded, dict):
        msg = f"設定ファイルの形式が不正です: {path}"
        raise InputError(msg)
    return loaded


def _normalize_pause_ms(raw: object) -> Mapping[str, int]:
    if not isinstance(raw, Mapping):
        msg = "pause_ms はマッピングである必要があります"
        raise InputError(msg)
    if set(raw.keys()) != PAUSE_KEYS:
        msg = "pause_ms のキーは paragraph, sentence, comma, other の 4 種が必要です"
        raise InputError(msg)
    normalized: dict[str, int] = {}
    for key, val in raw.items():
        if isinstance(val, bool) or not isinstance(val, int) or val < 0:
            msg = f"pause_ms[{key!r}] は 0 以上の整数である必要があります"
            raise InputError(msg)
        normalized[str(key)] = val
    return MappingProxyType(normalized)


def _normalize_cover(raw: object) -> Path | None:
    if raw is None:
        return None
    if isinstance(raw, (str, Path)):
        return Path(raw)
    msg = "cover はパス文字列または Path である必要があります"
    raise InputError(msg)


def _normalize_dictionaries(raw: object) -> tuple[Path, ...]:
    if isinstance(raw, (list, tuple)):
        result: list[Path] = []
        for item in raw:
            if not isinstance(item, (str, Path)):
                msg = "dictionaries の要素はパス文字列または Path である必要があります"
                raise InputError(msg)
            result.append(Path(item))
        return tuple(result)
    msg = "dictionaries はリストまたはタプルである必要があります"
    raise InputError(msg)


def normalize_chapters(raw: object) -> str | None:
    if raw is None:
        return None
    if isinstance(raw, str):
        return raw
    if isinstance(raw, int) and not isinstance(raw, bool):
        return str(raw)
    msg = "chapters は文字列である必要があります"
    raise InputError(msg)


def _parse_positive_chapter_number(token: str, spec: str) -> int:
    if not (token.isascii() and token.isdigit()):
        msg = f"chapters の指定が不正です: {spec}"
        raise InputError(msg)
    value = int(token)
    if value < MIN_CHAPTER_NUMBER:
        msg = f"chapters の番号は {MIN_CHAPTER_NUMBER} 以上である必要があります: {spec}"
        raise InputError(msg)
    return value


def parse_chapter_range(spec: str) -> tuple[int | None, int | None]:
    if not spec or spec == "-":
        msg = f"chapters の指定が不正です: {spec}"
        raise InputError(msg)
    left, sep, right = spec.partition("-")
    if not sep:
        number = _parse_positive_chapter_number(spec, spec)
        return (number, number)
    if "-" in right:
        msg = f"chapters の指定が不正です: {spec}"
        raise InputError(msg)
    first = _parse_positive_chapter_number(left, spec) if left else None
    last = _parse_positive_chapter_number(right, spec) if right else None
    if first is not None and last is not None and first > last:
        msg = f"chapters の範囲が不正です: {spec}"
        raise InputError(msg)
    return (first, last)


def _validate_engine_url(engine_url: str) -> None:
    parsed = urlparse(engine_url)
    if parsed.scheme not in ALLOWED_URL_SCHEMES or parsed.hostname not in LOOPBACK_HOSTS:
        msg = f"engine_url はループバックホストのみ許可されています: {engine_url}"
        raise InputError(msg)


def _validate_pdf_title_settings(settings: Settings) -> None:
    if settings.pdf_title_min_match < MIN_PDF_TITLE_MIN_MATCH:
        msg = f"pdf_title_min_match は {MIN_PDF_TITLE_MIN_MATCH} 以上である必要があります"
        raise InputError(msg)
    if settings.pdf_title_lines < MIN_PDF_TITLE_LINES:
        msg = f"pdf_title_lines は {MIN_PDF_TITLE_LINES} 以上である必要があります"
        raise InputError(msg)


def _validate_pdf_settings(settings: Settings) -> None:
    _validate_pdf_title_settings(settings)
    if settings.pdf_outline_level < MIN_PDF_OUTLINE_LEVEL:
        msg = f"pdf_outline_level は {MIN_PDF_OUTLINE_LEVEL} 以上である必要があります"
        raise InputError(msg)
    if not (0.0 < settings.pdf_footnote_size_ratio <= MAX_PDF_RATIO):
        msg = "pdf_footnote_size_ratio は (0, 1] の範囲で指定してください"
        raise InputError(msg)
    if not (0.0 < settings.pdf_repeat_page_ratio <= MAX_PDF_RATIO):
        msg = "pdf_repeat_page_ratio は (0, 1] の範囲で指定してください"
        raise InputError(msg)
    if settings.pdf_repeat_min_pages < MIN_PDF_REPEAT_MIN_PAGES:
        msg = f"pdf_repeat_min_pages は {MIN_PDF_REPEAT_MIN_PAGES} 以上である必要があります"
        raise InputError(msg)
    if settings.pdf_indent_tolerance_pt <= 0.0:
        msg = "pdf_indent_tolerance_pt は 0 より大きい必要があります"
        raise InputError(msg)
    if settings.pdf_paragraph_gap_ratio <= 0.0:
        msg = "pdf_paragraph_gap_ratio は 0 より大きい必要があります"
        raise InputError(msg)


def _validate_settings(settings: Settings) -> None:
    if not (MIN_SPEED_SCALE <= settings.speed_scale <= MAX_SPEED_SCALE):
        msg = f"speed_scale は {MIN_SPEED_SCALE}〜{MAX_SPEED_SCALE} の範囲で指定してください"
        raise InputError(msg)
    if settings.max_chunk_chars < settings.min_chunk_chars or settings.min_chunk_chars < 1:
        msg = "max_chunk_chars は min_chunk_chars 以上である必要があります"
        raise InputError(msg)
    if settings.retries < MIN_RETRIES:
        msg = f"retries は {MIN_RETRIES} 以上である必要があります"
        raise InputError(msg)
    if set(settings.pause_ms.keys()) != PAUSE_KEYS:
        msg = "pause_ms のキーは 4 種そろっている必要があります"
        raise InputError(msg)
    _validate_engine_url(settings.engine_url)
    if settings.cover is not None and not settings.cover.is_file():
        msg = f"カバー画像が見つかりません: {settings.cover}"
        raise InputError(msg)
    for dict_path in settings.dictionaries:
        if not dict_path.is_file():
            msg = f"辞書ファイルが見つかりません: {dict_path}"
            raise InputError(msg)
    if settings.chapters is not None:
        parse_chapter_range(settings.chapters)
    _validate_pdf_settings(settings)


def load_settings(
    path: Path | None = None,
    overrides: Mapping[str, object] | None = None,
) -> Settings:
    merged: dict[str, Any] = read_yaml(path) if path is not None else {}
    if overrides is not None:
        merged.update(overrides)

    valid_keys = {f.name for f in fields(Settings)}
    unknown_keys = set(merged.keys()) - valid_keys
    if unknown_keys:
        msg = f"未知の設定キーが含まれています: {sorted(unknown_keys)}"
        raise InputError(msg)

    if "pause_ms" in merged:
        merged["pause_ms"] = _normalize_pause_ms(merged["pause_ms"])
    if "cover" in merged:
        merged["cover"] = _normalize_cover(merged["cover"])
    if "dictionaries" in merged:
        merged["dictionaries"] = _normalize_dictionaries(merged["dictionaries"])
    if "chapters" in merged:
        merged["chapters"] = normalize_chapters(merged["chapters"])

    settings = Settings(**merged)
    _validate_settings(settings)
    return settings
