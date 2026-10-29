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

_ESCAPING_GRANDCHILD_SCRIPT = f"""\
import subprocess, sys, time
subprocess.Popen(
    [sys.executable, "-c", "import time; time.sleep({_GRANDCHILD_LIFETIME_SECONDS})"],
    start_new_session=True,
)
time.sleep({_GRANDCHILD_LIFETIME_SECONDS})
"""


@pytest.mark.requirement("REQ-2026-003-F07")
def test_timeout_does_not_wait_for_a_descendant_outside_the_process_group(tmp_path: Path) -> None:
    """A grandchild in its own session keeps the pipes open; the timeout still returns promptly."""
    script = tmp_path / "escaping_grandchild.py"
    script.write_text(_ESCAPING_GRANDCHILD_SCRIPT, encoding="utf-8")
    settings = SummarySettings(
        llm_command=(sys.executable, str(script)),
        llm_retries=0,
        llm_timeout_seconds=_TIMEOUT_SECONDS,
    )

    started = time.monotonic()
    with pytest.raises(EngineError):
        run_llm(settings, "prompt")

    assert time.monotonic() - started < _MAX_RETURN_SECONDS
