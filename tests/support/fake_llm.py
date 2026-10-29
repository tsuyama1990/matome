import json
import sys
from pathlib import Path
from typing import Any

_SCRIPT_PATH = Path(__file__).with_name("fake_llm_script.py")


def write_fake_llm(
    tmp_path: Path,
    *,
    config_name: str = "fake_llm_config.json",
    log_name: str = "fake_llm.log",
    **options: Any,
) -> tuple[tuple[str, ...], Path]:
    config_path = tmp_path / config_name
    log_path = tmp_path / log_name
    options.setdefault("log", str(log_path))
    config_path.write_text(json.dumps(options, ensure_ascii=False), encoding="utf-8")
    command = (sys.executable, str(_SCRIPT_PATH), str(config_path))
    return command, log_path


def read_calls(log: Path) -> list[dict[str, Any]]:
    if not log.is_file():
        return []
    calls: list[dict[str, Any]] = []
    for line in log.read_text(encoding="utf-8").splitlines():
        trimmed = line.strip()
        if trimmed:
            calls.append(json.loads(trimmed))
    return calls
