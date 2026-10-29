import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

_USAGE_EXIT_CODE = 2
_DEFAULT_CHILD_SLEEP_SECONDS = 120
_DEFAULT_FAIL_EXIT_CODE = 1
_MIN_ARG_COUNT_WITH_PROMPT = 3


def _record_call(config_path: Path, config: dict[str, Any], prompt: str) -> int:
    log_path_str = config.get("log")
    if log_path_str:
        log_path = Path(log_path_str)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        call_index = (
            len(log_path.read_text(encoding="utf-8").splitlines()) if log_path.is_file() else 0
        )
        log_entry = json.dumps({"prompt": prompt, "argv": sys.argv}, ensure_ascii=False)
        with log_path.open("a", encoding="utf-8") as file:
            file.write(log_entry + "\n")
        return call_index

    state_path = config_path.with_name(config_path.name + ".count")
    call_index = 0
    if state_path.is_file():
        call_index = int(state_path.read_text(encoding="utf-8").strip() or "0")
    state_path.write_text(str(call_index + 1), encoding="utf-8")
    return call_index


def _spawn_child_if_requested(config: dict[str, Any]) -> None:
    child_pid_file = config.get("child_pid_file")
    if not child_pid_file:
        return
    child_path = Path(child_pid_file)
    child_path.parent.mkdir(parents=True, exist_ok=True)
    child_proc = subprocess.Popen(  # noqa: S603
        [sys.executable, "-c", f"import time; time.sleep({_DEFAULT_CHILD_SLEEP_SECONDS})"]
    )
    child_path.write_text(str(child_proc.pid), encoding="utf-8")
    if "sleep" not in config:
        time.sleep(_DEFAULT_CHILD_SLEEP_SECONDS)


def _should_fail(config: dict[str, Any], call_index: int, prompt: str) -> bool:
    call_number = call_index + 1
    fail_calls = config.get("fail_calls", [])
    if call_number in fail_calls:
        return True
    fail_when = config.get("fail_when")
    if fail_when and fail_when in prompt:
        return True
    exit_code_cfg = config.get("exit_code")
    return bool(exit_code_cfg is not None and int(exit_code_cfg) != 0)


def _output_response(config: dict[str, Any], call_index: int, prompt: str) -> None:
    raw_hex = config.get("raw_hex")
    if raw_hex is not None:
        raw_bytes = bytes.fromhex(raw_hex) if raw_hex else b""
        sys.stdout.buffer.write(raw_bytes)
        sys.stdout.buffer.flush()
        return

    if config.get("echo"):
        sys.stdout.write(prompt)
        sys.stdout.flush()
        return

    replies = config.get("replies")
    if replies:
        reply_idx = min(call_index, len(replies) - 1)
        sys.stdout.write(str(replies[reply_idx]))
    else:
        sys.stdout.write("要約の本文です。")
    sys.stdout.flush()


def main() -> None:
    if len(sys.argv) < 2:
        sys.stderr.write("Usage: fake_llm_script.py <config_json> [args...] <prompt>\n")
        sys.exit(_USAGE_EXIT_CODE)

    config_path = Path(sys.argv[1])
    config = json.loads(config_path.read_text(encoding="utf-8")) if config_path.is_file() else {}
    prompt = sys.argv[-1] if len(sys.argv) >= _MIN_ARG_COUNT_WITH_PROMPT else ""

    call_index = _record_call(config_path, config, prompt)
    _spawn_child_if_requested(config)

    sleep_sec = config.get("sleep")
    if sleep_sec is not None:
        time.sleep(float(sleep_sec))

    if _should_fail(config, call_index, prompt):
        exit_code_cfg = config.get("exit_code")
        code = (
            int(exit_code_cfg)
            if exit_code_cfg is not None and int(exit_code_cfg) != 0
            else _DEFAULT_FAIL_EXIT_CODE
        )
        sys.stderr.write(f"LLM command failed (call {call_index + 1})\n")
        sys.exit(code)

    _output_response(config, call_index, prompt)
    sys.exit(0)


if __name__ == "__main__":
    main()
