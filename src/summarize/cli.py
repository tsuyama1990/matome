import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from src.summarize.pipeline import run
from src.summarize.settings import load_summary_settings
from src.txt2speech.cli import EXIT_ENGINE_ERROR, EXIT_INPUT_ERROR, EXIT_OK
from src.txt2speech.errors import EngineError, InputError


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="summarize")
    parser.add_argument("input_path", metavar="INPUT", type=Path)
    parser.add_argument("-o", "--output", required=True, type=Path, dest="output")
    parser.add_argument("--config", type=Path, default=None, dest="config")
    parser.add_argument("--chapters", type=str, default=None, dest="chapters")
    return parser


def _report_progress(position: int, total: int, title: str) -> None:
    sys.stderr.write(f"要約 {position}/{total}: {title}\n")


def main(argv: Sequence[str] | None = None) -> int:
    try:
        args = _build_parser().parse_args(list(argv) if argv is not None else None)
    except SystemExit as exc:
        return EXIT_OK if exc.code == 0 else EXIT_INPUT_ERROR
    overrides = {"chapters": args.chapters} if args.chapters is not None else None
    try:
        settings = load_summary_settings(args.config, overrides)
        sys.stderr.write(f"本文を {settings.llm_command[0]} に送ります\n")
        summary_path = run(args.input_path, args.output, settings, progress_cb=_report_progress)
    except InputError as exc:
        sys.stderr.write(f"{exc}\n")
        return EXIT_INPUT_ERROR
    except EngineError as exc:
        sys.stderr.write(f"{exc}\n")
        return EXIT_ENGINE_ERROR
    sys.stdout.write(f"{summary_path}\n")
    return EXIT_OK
