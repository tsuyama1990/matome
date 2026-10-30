import hashlib
import json
import re
from collections.abc import Sequence
from pathlib import Path

from src.summarize.settings import SummarySettings

_KEY_HEX_CHARS = 16
_HEADING_MARKS = re.compile(r"^#+\s*", re.MULTILINE)


def cache_key(draft_prompt: str, density_template: str, settings: SummarySettings) -> str:
    material = json.dumps(
        {
            "draft_prompt": draft_prompt,
            "density_template": density_template,
            "rounds": settings.density_rounds,
            "command": list(settings.llm_command),
        },
        sort_keys=True,
        ensure_ascii=False,
    )
    return hashlib.sha256(material.encode("utf-8")).hexdigest()[:_KEY_HEX_CHARS]


def _entry_path(work_dir: Path, index: int, key: str) -> Path:
    return work_dir / f"{index:02d}_{key}.txt"


def write_atomic(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    try:
        tmp.write_text(text, encoding="utf-8")
        tmp.replace(path)
    except BaseException:
        tmp.unlink(missing_ok=True)
        raise


def load(work_dir: Path, index: int, key: str) -> str | None:
    path = _entry_path(work_dir, index, key)
    return path.read_text(encoding="utf-8") if path.is_file() else None


def save(work_dir: Path, index: int, key: str, text: str) -> None:
    write_atomic(_entry_path(work_dir, index, key), text)


def render(items: Sequence[tuple[str, str]]) -> str:
    sections = []
    for title, summary in items:
        flat_title = _HEADING_MARKS.sub("", " ".join(title.split()))
        sections.append(f"# {flat_title}\n\n{_HEADING_MARKS.sub('', summary)}")
    return "\n\n".join(sections) + "\n"
