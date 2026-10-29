import json
import sys
from pathlib import Path
from typing import Any

import pytest

from src.summarize.cli import main
from src.txt2speech.cli import EXIT_ENGINE_ERROR, EXIT_INPUT_ERROR, EXIT_OK
from tests.support.fake_llm import write_fake_llm


def _write_input_and_config(tmp_path: Path, **llm_options: Any) -> tuple[Path, Path]:
    input_path = tmp_path / "book.txt"
    input_path.write_text("第1章\n本文です。\n", encoding="utf-8")
    command, _log = write_fake_llm(tmp_path, **llm_options)
    config_path = tmp_path / "config.json"
    config = {"llm_command": list(command), "llm_retries": 0, "llm_retry_wait_seconds": 0.01}
    config_path.write_text(json.dumps(config), encoding="utf-8")
    return input_path, config_path


@pytest.mark.requirement("REQ-2026-003-F08")
def test_main_success_prints_summary_path_and_notice(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """main returns 0, prints the summary path to stdout, and announces the external send first."""
    input_path, config_path = _write_input_and_config(tmp_path, replies=["要約です。"])
    out_dir = tmp_path / "out"

    code = main([str(input_path), "--out-dir", str(out_dir), "--config", str(config_path)])

    captured = capsys.readouterr()
    assert code == EXIT_OK
    assert captured.out.strip() == str(out_dir / "summary.md")
    assert captured.err.splitlines()[0] == f"本文を {sys.executable} に送ります"
    assert "要約 1/1: 第1章" in captured.err


@pytest.mark.requirement("REQ-2026-003-F08")
def test_main_llm_failure_returns_engine_error_code(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A failing LLM command ends with the engine-error exit code."""
    input_path, config_path = _write_input_and_config(tmp_path, fail_calls=[1])

    code = main([str(input_path), "--out-dir", str(tmp_path / "out"), "--config", str(config_path)])

    captured = capsys.readouterr()
    assert code == EXIT_ENGINE_ERROR
    assert "第1章" in captured.err


@pytest.mark.requirement("REQ-2026-003-F08")
def test_main_missing_input_returns_input_error_code(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A missing input file ends with the input-error exit code."""
    code = main([str(tmp_path / "missing.txt"), "--out-dir", str(tmp_path / "out")])

    captured = capsys.readouterr()
    assert code == EXIT_INPUT_ERROR
    assert "missing.txt" in captured.err


@pytest.mark.requirement("REQ-2026-003-F08")
def test_main_argument_errors_and_help(capsys: pytest.CaptureFixture[str]) -> None:
    """A missing required option is an input error; --help exits cleanly."""
    assert main(["book.txt"]) == EXIT_INPUT_ERROR
    assert main(["--help"]) == EXIT_OK
    capsys.readouterr()
