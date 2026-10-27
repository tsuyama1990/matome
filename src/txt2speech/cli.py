import argparse
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from tqdm import tqdm

from src.txt2speech.config import Settings, load_settings
from src.txt2speech.errors import EngineError, InputError
from src.txt2speech.pipeline import Encoder, SynthClient, make_encoder, run
from src.txt2speech.voicevox import VoicevoxClient

EXIT_OK = 0
EXIT_INPUT_ERROR = 2
EXIT_ENGINE_ERROR = 3

_ARG_TO_SETTINGS_KEY: tuple[tuple[str, str], ...] = (
    ("speaker", "speaker"),
    ("engine_url", "engine_url"),
    ("speed_scale", "speed_scale"),
    ("max_chars", "max_chunk_chars"),
    ("ffmpeg", "ffmpeg_path"),
    ("cover", "cover"),
    ("album", "album"),
    ("voice_name", "voice_name"),
)


class _ProgressReporter:
    def __init__(self) -> None:
        self._bar: Any = None
        self._current_chapter: int | None = None
        self._last_done: int = 0

    def update(
        self,
        chapter_index: int,
        total_chapters: int,
        done_chunks: int,
        total_chunks: int,
    ) -> None:
        if self._bar is None or self._current_chapter != chapter_index:
            self.close()
            self._current_chapter = chapter_index
            self._last_done = 0
            # Explicitly enable tqdm output so progress is written even when stderr is not a TTY.
            self._bar = tqdm(
                total=total_chunks,
                desc=f"章 {chapter_index}/{total_chapters}",
                unit="chunk",
                file=sys.stderr,
                disable=False,
            )
        delta = done_chunks - self._last_done
        if delta > 0:
            self._bar.update(delta)
            self._last_done = done_chunks

    def close(self) -> None:
        if self._bar is not None:
            self._bar.close()
            self._bar = None


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="txt2speech")
    parser.add_argument("input_path", metavar="INPUT", type=Path)
    parser.add_argument("-o", "--output", required=True, type=Path, dest="output")
    parser.add_argument("--config", type=Path, default=None, dest="config")
    parser.add_argument("--speaker", type=int, default=None, dest="speaker")
    parser.add_argument("--engine-url", type=str, default=None, dest="engine_url")
    parser.add_argument("--speed-scale", type=float, default=None, dest="speed_scale")
    parser.add_argument("--max-chars", type=int, default=None, dest="max_chars")
    parser.add_argument("--ffmpeg", type=str, default=None, dest="ffmpeg")
    parser.add_argument("--cover", type=Path, default=None, dest="cover")
    parser.add_argument("--album", type=str, default=None, dest="album")
    parser.add_argument("--voice-name", type=str, default=None, dest="voice_name")
    parser.add_argument(
        "--dictionary",
        type=Path,
        action="append",
        default=None,
        dest="dictionary",
    )
    return parser


def _build_overrides(args: argparse.Namespace) -> dict[str, object]:
    overrides: dict[str, object] = {}
    for arg_name, settings_key in _ARG_TO_SETTINGS_KEY:
        value = getattr(args, arg_name)
        if value is not None:
            overrides[settings_key] = value
    if args.dictionary is not None:
        overrides["dictionaries"] = tuple(args.dictionary)
    return overrides


def _execute_pipeline(
    input_path: Path,
    out_dir: Path,
    settings: Settings,
    client: SynthClient | None,
    encoder: Encoder | None,
) -> list[Path]:
    reporter = _ProgressReporter()
    active_encoder = encoder if encoder is not None else make_encoder(settings)
    try:
        if client is not None:
            return run(
                input_path=input_path,
                out_dir=out_dir,
                settings=settings,
                client=client,
                encoder=active_encoder,
                progress_cb=reporter.update,
            )
        with VoicevoxClient(settings) as real_client:
            return run(
                input_path=input_path,
                out_dir=out_dir,
                settings=settings,
                client=real_client,
                encoder=active_encoder,
                progress_cb=reporter.update,
            )
    finally:
        reporter.close()


def main(
    argv: Sequence[str] | None = None,
    *,
    client: SynthClient | None = None,
    encoder: Encoder | None = None,
) -> int:
    parser = _build_parser()
    try:
        args = parser.parse_args(list(argv) if argv is not None else None)
    except SystemExit as exc:
        if exc.code == 0:
            return EXIT_OK
        return EXIT_INPUT_ERROR

    try:
        overrides = _build_overrides(args)
        settings = load_settings(args.config, overrides)
        mp3_paths = _execute_pipeline(
            input_path=args.input_path,
            out_dir=args.output,
            settings=settings,
            client=client,
            encoder=encoder,
        )
    except InputError as exc:
        sys.stderr.write(f"{exc}\n")
        return EXIT_INPUT_ERROR
    except EngineError as exc:
        sys.stderr.write(f"{exc}\n")
        return EXIT_ENGINE_ERROR

    for mp3_path in mp3_paths:
        sys.stdout.write(f"{mp3_path}\n")
    return EXIT_OK
