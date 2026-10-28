import hashlib
import json
import shutil
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from src.txt2speech.config import Settings


@dataclass(frozen=True)
class ProgressState:
    fingerprint: str
    done_chapters: list[int]

    def __getitem__(self, key: str) -> Any:
        if key == "fingerprint":
            return self.fingerprint
        if key == "done_chapters":
            return self.done_chapters
        raise KeyError(key)


def fingerprint(
    input_bytes: bytes,
    dictionary_texts: Sequence[str],
    cover_bytes: bytes | None,
    settings: Settings,
) -> str:
    # Hash content and output-affecting settings only; exclude file paths.
    payload: dict[str, Any] = {
        "input_sha256": hashlib.sha256(input_bytes).hexdigest(),
        "dictionaries": list(dictionary_texts),
        "cover_sha256": hashlib.sha256(cover_bytes or b"").hexdigest(),
        "settings": {
            "speaker": settings.speaker,
            "speed_scale": settings.speed_scale,
            "pitch_scale": settings.pitch_scale,
            "intonation_scale": settings.intonation_scale,
            "volume_scale": settings.volume_scale,
            "max_chunk_chars": settings.max_chunk_chars,
            "min_chunk_chars": settings.min_chunk_chars,
            "pause_ms": dict(sorted(settings.pause_ms.items())),
            "loudness_lufs": settings.loudness_lufs,
            "true_peak_dbfs": settings.true_peak_dbfs,
            "loudness_range": settings.loudness_range,
            "sample_rate_hz": settings.sample_rate_hz,
            "bitrate": settings.bitrate,
            "voice_name": settings.voice_name,
            "album": settings.album,
            "genre": settings.genre,
            "chapters": settings.chapters,
        },
    }
    serialized = json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(serialized).hexdigest()


def _clear_work_dir_contents(work_dir: Path) -> None:
    if not work_dir.is_dir():
        return
    for child in work_dir.iterdir():
        if child.is_dir():
            shutil.rmtree(child)
        else:
            child.unlink()


def _parse_done_chapters(raw_chapters: object) -> set[int] | None:
    if not isinstance(raw_chapters, list):
        return None
    done: set[int] = set()
    for item in raw_chapters:
        if isinstance(item, bool) or not isinstance(item, int):
            return None
        done.add(item)
    return done


class Progress:
    def __init__(self, progress_path: Path, work_dir: Path, fingerprint: str) -> None:
        self.progress_path = progress_path
        self.work_dir = work_dir
        self.fingerprint = fingerprint
        self._done_chapters: set[int] = set()

    @property
    def done_chapters(self) -> list[int]:
        return sorted(self._done_chapters)

    def _read_matching_done_chapters(self) -> set[int] | None:
        if not self.progress_path.is_file():
            return None
        try:
            loaded = json.loads(self.progress_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None
        if not isinstance(loaded, dict) or loaded.get("fingerprint") != self.fingerprint:
            return None
        return _parse_done_chapters(loaded.get("done_chapters"))

    def load(self) -> ProgressState:
        matching = self._read_matching_done_chapters()
        if matching is None:
            _clear_work_dir_contents(self.work_dir)
            self._done_chapters = set()
            return ProgressState(fingerprint=self.fingerprint, done_chapters=[])

        self._done_chapters = matching
        return ProgressState(
            fingerprint=self.fingerprint,
            done_chapters=sorted(self._done_chapters),
        )

    def mark_chapter_done(self, index: int) -> None:
        if not self._done_chapters:
            existing = self._read_matching_done_chapters()
            if existing is not None:
                self._done_chapters = existing

        self._done_chapters.add(index)
        self.progress_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "fingerprint": self.fingerprint,
            "done_chapters": sorted(self._done_chapters),
        }
        # Write to a sibling temporary file first, then atomically replace the progress file.
        tmp_path = self.progress_path.with_name(f"{self.progress_path.name}.tmp")
        tmp_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        tmp_path.replace(self.progress_path)

    def clear(self) -> None:
        self._done_chapters.clear()
        self.progress_path.unlink(missing_ok=True)
        if self.work_dir.exists():
            shutil.rmtree(self.work_dir)
