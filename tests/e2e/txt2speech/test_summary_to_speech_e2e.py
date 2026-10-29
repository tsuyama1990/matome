import json
import os
import subprocess
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path

import pytest

from tests.e2e.txt2speech.conftest import FakeVoicevoxServer
from tests.support.fake_llm import write_fake_llm

_PROJECT_ROOT_DEPTH = 3
_PROJECT_ROOT = Path(__file__).resolve().parents[_PROJECT_ROOT_DEPTH]
_EXIT_OK = 0
_TWO_CHAPTERS_TEXT = "# 第1章 基礎\n第1章の長い本文です。\n\n# 第2章 応用\n第2章の長い本文です。\n"


def _run_cli(
    module: str,
    args: Sequence[str],
    extra_env: Mapping[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    if extra_env is not None:
        env.update(extra_env)
    cmd = [sys.executable, "-m", module, *args]
    return subprocess.run(  # noqa: S603
        cmd,
        cwd=_PROJECT_ROOT,
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )


@pytest.mark.requirement("REQ-2026-003-F05")
def test_sum_e12_summary_to_speech_pipeline(
    tmp_path: Path,
    fake_voicevox: FakeVoicevoxServer,
) -> None:
    """SUM-E12: summary.md piped into txt2speech creates chapter-wise MP3 files."""
    input_path = tmp_path / "textbook.txt"
    input_path.write_text(_TWO_CHAPTERS_TEXT, encoding="utf-8")

    out_summary_dir = tmp_path / "out_summary"
    cmd, _log = write_fake_llm(
        tmp_path,
        replies=["第1章の要約本文です。", "第2章の要約本文です。"],
    )
    cfg_path = tmp_path / "summarize_config.json"
    cfg_path.write_text(
        json.dumps({"llm_command": list(cmd)}, ensure_ascii=False),
        encoding="utf-8",
    )

    # 1. Run summarize CLI
    summarize_proc = _run_cli(
        "src.summarize",
        [str(input_path), "-o", str(out_summary_dir), "--config", str(cfg_path)],
    )
    assert summarize_proc.returncode == _EXIT_OK
    summary_path = out_summary_dir / "summary.md"
    assert summary_path.is_file()

    # 2. Run txt2speech CLI with summary.md as input
    out_speech_dir = tmp_path / "out_speech"
    txt2speech_proc = _run_cli(
        "src.txt2speech",
        [str(summary_path), "-o", str(out_speech_dir), "--engine-url", fake_voicevox.url],
    )
    assert txt2speech_proc.returncode == _EXIT_OK

    mp3_files = sorted(out_speech_dir.glob("*.mp3"))
    assert len(mp3_files) == 2
    assert mp3_files[0].name == "01_第1章 基礎.mp3"
    assert mp3_files[1].name == "02_第2章 応用.mp3"
