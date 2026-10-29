import contextlib
import os
import signal
import subprocess
import time
from collections.abc import Callable

from src.summarize.settings import SummarySettings
from src.txt2speech.errors import EngineError

_STDERR_TAIL_CHARS = 200
_BACKOFF_FACTOR = 2


def _attempt(command: list[str], timeout: float) -> tuple[str | None, str]:
    proc = subprocess.Popen(  # noqa: S603
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        start_new_session=True,
    )
    try:
        out, err = proc.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        with contextlib.suppress(ProcessLookupError):
            os.killpg(proc.pid, signal.SIGKILL)
        proc.communicate()
        return None, "タイムアウト"
    tail = err.decode("utf-8", errors="replace")[-_STDERR_TAIL_CHARS:]
    if proc.returncode != 0:
        return None, f"終了コード {proc.returncode}: {tail}"
    try:
        text = out.decode("utf-8")
    except UnicodeDecodeError:
        return None, "標準出力が UTF-8 として読めません"
    if not text.strip():
        return None, f"標準出力が空です: {tail}"
    return text, ""


def run_llm(
    settings: SummarySettings,
    prompt: str,
    sleep: Callable[[float], None] = time.sleep,
) -> str:
    command = [*settings.llm_command, prompt]
    head = settings.llm_command[0]
    reason = ""
    for attempt in range(1 + settings.llm_retries):
        if attempt:
            sleep(settings.llm_retry_wait_seconds * _BACKOFF_FACTOR ** (attempt - 1))
        try:
            text, reason = _attempt(command, settings.llm_timeout_seconds)
        except OSError as exc:
            msg = f"LLM コマンドを実行できません ({head}): {exc}"
            raise EngineError(msg) from exc
        if text is not None:
            return text
    msg = f"LLM の実行に失敗しました ({head}): {reason}"
    raise EngineError(msg)
