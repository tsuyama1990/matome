import contextlib
import os
import signal
import sys
import time
from pathlib import Path

import pytest

from src.summarize.llm import run_llm
from src.summarize.settings import SummarySettings
from src.txt2speech.errors import EngineError

_TIMEOUT_SECONDS = 0.5
_MAX_RETURN_SECONDS = 5.0
_GRANDCHILD_LIFETIME_SECONDS = 20
_REPLY = "要約です。"

# The grandchild leaves the process group (new session) and keeps the inherited stdout open.
_ESCAPING_GRANDCHILD_SCRIPT = f"""\
import pathlib, subprocess, sys, time
child = subprocess.Popen(
    [sys.executable, "-c", "import time; time.sleep({_GRANDCHILD_LIFETIME_SECONDS})"],
    start_new_session=True,
)
pathlib.Path(sys.argv[1]).write_text(str(child.pid))
if sys.argv[2] == "reply":
    sys.stdout.write({_REPLY!r})
    sys.stdout.flush()
else:
    time.sleep({_GRANDCHILD_LIFETIME_SECONDS})
"""


def _run_with_escaping_grandchild(
    tmp_path: Path, mode: str, settings_overrides: dict[str, float | int]
) -> tuple[str | None, float]:
    script = tmp_path / "escaping_grandchild.py"
    script.write_text(_ESCAPING_GRANDCHILD_SCRIPT, encoding="utf-8")
    pid_file = tmp_path / "grandchild.pid"
    settings = SummarySettings(
        llm_command=(sys.executable, str(script), str(pid_file), mode),
        llm_retries=0,
        **settings_overrides,  # type: ignore[arg-type]
    )
    started = time.monotonic()
    result: str | None = None
    try:
        try:
            result = run_llm(settings, "prompt")
        except EngineError:
            result = None
        return result, time.monotonic() - started
    finally:
        if pid_file.is_file():
            with contextlib.suppress(ProcessLookupError):
                os.kill(int(pid_file.read_text(encoding="utf-8")), signal.SIGKILL)


@pytest.mark.requirement("REQ-2026-003-F07")
def test_timeout_does_not_wait_for_a_descendant_outside_the_process_group(tmp_path: Path) -> None:
    """A grandchild in its own session keeps the output open; the timeout still returns promptly."""
    result, elapsed = _run_with_escaping_grandchild(
        tmp_path, "hang", {"llm_timeout_seconds": _TIMEOUT_SECONDS}
    )

    assert result is None
    assert elapsed < _MAX_RETURN_SECONDS


@pytest.mark.requirement("REQ-2026-003-F07")
def test_clean_exit_does_not_wait_for_a_descendant_holding_the_output(tmp_path: Path) -> None:
    """A command that replied and exited 0 succeeds at once, though a grandchild keeps stdout."""
    result, elapsed = _run_with_escaping_grandchild(tmp_path, "reply", {})

    assert result == _REPLY
    assert elapsed < _MAX_RETURN_SECONDS
