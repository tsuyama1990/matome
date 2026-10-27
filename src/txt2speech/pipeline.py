import shutil
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from src.txt2speech import mp3
from src.txt2speech.audio import concat_wav_bytes, join_wav_files, write_wav
from src.txt2speech.chunking import halve, split_chunks
from src.txt2speech.config import (
    DEFAULT_MIN_CHUNK_CHARS,
    MIN_CHAPTER_INDEX_WIDTH,
    Settings,
)
from src.txt2speech.dictionary import DictEntry, parse_dictionary
from src.txt2speech.errors import EngineError, InputError, ResourceExhausted
from src.txt2speech.models import Chapter, Chunk
from src.txt2speech.preprocess import normalize
from src.txt2speech.progress import Progress, fingerprint
from src.txt2speech.structure import chapter_filename, split_chapters
from src.txt2speech.text_io import read_text

_CHUNK_INDEX_WIDTH = 4
_JOINED_WAV_NAME = "joined.wav"


class SynthClient(Protocol):
    def check(self) -> None: ...

    def register(self, entry: DictEntry) -> None: ...

    def synthesize(self, text: str) -> bytes: ...


Encoder = Callable[[Path, Path, str, str, int], None]
ProgressCallback = Callable[[int, int, int, int], None]


@dataclass(frozen=True)
class _LoadedInputs:
    input_bytes: bytes
    chapters: list[Chapter]
    dictionary_texts: list[str]
    dict_entries: list[DictEntry]
    cover_bytes: bytes | None


def _noop_progress(
    _chapter_index: int,
    _total_chapters: int,
    _done_chunks: int,
    _total_chunks: int,
) -> None:
    return None


def make_encoder(settings: Settings) -> Encoder:
    def _encode(
        wav_path: Path,
        out_path: Path,
        title: str,
        album: str,
        track: int,
    ) -> None:
        mp3.encode(
            wav_path=wav_path,
            out_path=out_path,
            title=title,
            album=album,
            track=track,
            settings=settings,
        )

    return _encode


def synthesize_with_halving(
    text: str,
    client: SynthClient,
    min_chars: int | Settings = DEFAULT_MIN_CHUNK_CHARS,
) -> bytes:
    effective_min = min_chars.min_chunk_chars if isinstance(min_chars, Settings) else min_chars
    try:
        return client.synthesize(text)
    except ResourceExhausted as exc:
        halved = halve(text, effective_min)
        if halved is None:
            msg = f"チャンクをこれ以上分割できません (len={len(text)}, min_chars={effective_min})"
            raise EngineError(msg) from exc
        first_half, second_half = halved
        first_wav = synthesize_with_halving(first_half, client, effective_min)
        second_wav = synthesize_with_halving(second_half, client, effective_min)
        return concat_wav_bytes([first_wav, second_wav])


def _load_dictionaries(paths: Sequence[Path]) -> tuple[list[str], list[DictEntry]]:
    texts: list[str] = []
    entries: list[DictEntry] = []
    for dict_path in paths:
        dict_text = read_text(dict_path)
        texts.append(dict_text)
        entries.extend(parse_dictionary(dict_text, str(dict_path)))
    return texts, entries


def _read_cover_bytes(cover_path: Path | None) -> bytes | None:
    if cover_path is None:
        return None
    if not cover_path.is_file():
        msg = f"カバー画像が見つかりません: {cover_path}"
        raise InputError(msg)
    try:
        return cover_path.read_bytes()
    except OSError as exc:
        msg = f"カバー画像の読み込みに失敗しました: {cover_path}"
        raise InputError(msg) from exc


def _load_inputs(input_path: Path, settings: Settings) -> _LoadedInputs:
    text = read_text(input_path)
    try:
        input_bytes = input_path.read_bytes()
    except OSError as exc:
        msg = f"入力ファイルの読み込みに失敗しました: {input_path}"
        raise InputError(msg) from exc
    chapters = split_chapters(text)
    dictionary_texts, dict_entries = _load_dictionaries(settings.dictionaries)
    cover_bytes = _read_cover_bytes(settings.cover)
    return _LoadedInputs(
        input_bytes=input_bytes,
        chapters=chapters,
        dictionary_texts=dictionary_texts,
        dict_entries=dict_entries,
        cover_bytes=cover_bytes,
    )


def _synthesize_chapter_chunks(
    chunks: Sequence[Chunk],
    chapter_work_dir: Path,
    chapter_index: int,
    total_chapters: int,
    settings: Settings,
    client: SynthClient,
    progress_cb: ProgressCallback,
) -> list[Path]:
    total_chunks = len(chunks)
    chunk_paths: list[Path] = []
    for chunk_index, chunk in enumerate(chunks, start=1):
        chunk_wav_path = chapter_work_dir / f"{chunk_index:0{_CHUNK_INDEX_WIDTH}d}.wav"
        if not chunk_wav_path.is_file():
            wav_bytes = synthesize_with_halving(
                chunk.text,
                client,
                settings.min_chunk_chars,
            )
            write_wav(chunk_wav_path, wav_bytes)
        chunk_paths.append(chunk_wav_path)
        progress_cb(chapter_index, total_chapters, chunk_index, total_chunks)
    return chunk_paths


def _process_chapter(
    chapter_index: int,
    chapter: Chapter,
    total_chapters: int,
    width: int,
    default_stem: str,
    out_dir: Path,
    work_dir: Path,
    done_set: set[int],
    settings: Settings,
    client: SynthClient,
    encoder: Encoder,
    progress_cb: ProgressCallback,
    prog: Progress,
) -> Path | None:
    mp3_path = out_dir / chapter_filename(chapter_index, chapter.title, width)
    if chapter_index in done_set and mp3_path.is_file():
        return mp3_path

    normalized_body = normalize(chapter.body)
    chunks = split_chunks(normalized_body, settings.max_chunk_chars)
    if not chunks:
        return None

    chapter_work_dir = work_dir / f"ch{chapter_index:0{width}d}"
    chunk_paths = _synthesize_chapter_chunks(
        chunks=chunks,
        chapter_work_dir=chapter_work_dir,
        chapter_index=chapter_index,
        total_chapters=total_chapters,
        settings=settings,
        client=client,
        progress_cb=progress_cb,
    )

    joined_wav_path = chapter_work_dir / _JOINED_WAV_NAME
    boundaries = [chunk.boundary for chunk in chunks]
    join_wav_files(chunk_paths, boundaries, settings, joined_wav_path)

    effective_title = chapter.title if chapter.title else default_stem
    effective_album = settings.album if settings.album is not None else default_stem
    encoder(joined_wav_path, mp3_path, effective_title, effective_album, chapter_index)

    shutil.rmtree(chapter_work_dir)
    prog.mark_chapter_done(chapter_index)
    return mp3_path


def run(
    input_path: Path,
    out_dir: Path,
    settings: Settings,
    client: SynthClient,
    encoder: Encoder | None = None,
    progress_cb: ProgressCallback | None = None,
) -> list[Path]:
    # Validate and read all user inputs before checking external tools or touching out_dir.
    loaded = _load_inputs(input_path, settings)

    mp3.check(settings)
    client.check()
    out_dir.mkdir(parents=True, exist_ok=True)

    fp = fingerprint(
        loaded.input_bytes,
        loaded.dictionary_texts,
        loaded.cover_bytes,
        settings,
    )
    work_dir = out_dir / settings.work_dir_name
    progress_path = out_dir / settings.progress_file_name
    prog = Progress(progress_path=progress_path, work_dir=work_dir, fingerprint=fp)
    state = prog.load()
    done_set = set(state.done_chapters)

    for entry in loaded.dict_entries:
        client.register(entry)

    active_encoder = encoder if encoder is not None else make_encoder(settings)
    active_progress_cb = progress_cb if progress_cb is not None else _noop_progress
    total_chapters = len(loaded.chapters)
    width = max(MIN_CHAPTER_INDEX_WIDTH, len(str(total_chapters)))
    default_stem = input_path.stem

    mp3_paths: list[Path] = []
    for chapter_index, chapter in enumerate(loaded.chapters, start=1):
        mp3_path = _process_chapter(
            chapter_index=chapter_index,
            chapter=chapter,
            total_chapters=total_chapters,
            width=width,
            default_stem=default_stem,
            out_dir=out_dir,
            work_dir=work_dir,
            done_set=done_set,
            settings=settings,
            client=client,
            encoder=active_encoder,
            progress_cb=active_progress_cb,
            prog=prog,
        )
        if mp3_path is not None:
            mp3_paths.append(mp3_path)

    prog.clear()
    return mp3_paths
